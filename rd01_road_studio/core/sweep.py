"""Sweep a compiled cross-section along a rail into quad-topology road pieces (spec §3.2).

Topology rules enforced by construction:
- every surface face is a quad; vertices are shared through an explicit (loop, column) grid;
- hard template columns become sharp edges AND UV seams; slot changes are seams only;
- UV1 u is the 3D run length on each band's reference column, so joints stay radial on curves;
- outer edges get a skirt (SKIRT closure) and free ends an end curtain; port ends stay open
  so spline-mesh / kit pieces join without internal faces.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from .qmesh import QMesh, Part, Kind, ID_COLOURS, UV_LAYERS, COLOR_ID, COLOR_MASK, edge_key
from .section import Template, Segment
from .rail import Rail, sample_stations, check_offset
from .piece import Piece, Socket
from . import uv as uvlib

MARK_LIFT = 0.003          # raised markings sit 3 mm above the surface (spec D13)
MARK_SINK = 0.002          # their side walls sink 2 mm into it, so no gap shows at grazing angles
PAVED = {Part.LANE, Part.SHOULDER, Part.MEDIAN_FLUSH, Part.GUTTER}
UNPAVED = {Part.VERGE, Part.GRAVEL}


@dataclass
class RoadOptions:
    name: str = 'SM_RD01_Road'
    max_step: float = 1.0               # longitudinal edge spacing on straights (m)
    sag_tol: float = 0.01               # chord error tolerance on curves (m)
    uniform: bool = False               # equal station spacing (spline-mesh kit pieces)
    chunk_length: float = 32.0          # split long roads into chunks (m); keeps |UV| ≲ 16 for UE half floats
    port_start: bool = False            # True = open end (joins a port), False = end curtain
    port_end: bool = False
    markings: bool = True
    dash_period_fit: bool = True        # scale dash cycles so they divide the road length
    skirt: bool = True


@dataclass
class _Grid:
    stations: list[float]
    pos: list[list[tuple]]              # [loop][column] → (x, y, z) in source space
    tangent: list[tuple[float, float]]
    run: list[list[float]]              # [column][loop] → cumulative 3D length along that column


def _build_grid(rail: Rail, tpl: Template, stations: list[float]) -> _Grid:
    pos, tans = [], []
    for s in stations:
        tan = rail.tangent(s)
        tans.append(tan)
        pos.append([rail.offset_point(s, c.t, c.z, tan) for c in tpl.columns])
    run = []
    for j in range(len(tpl.columns)):
        acc = [0.0]
        for i in range(1, len(stations)):
            acc.append(acc[-1] + math.dist(pos[i - 1][j], pos[i][j]))
        run.append(acc)
    return _Grid(stations, pos, tans, run)


def _dash_intervals(pattern: str, length: float, fit: bool) -> list[tuple[float, float]]:
    if pattern == 'SOLID':
        return [(0.0, length)]
    on, off = (float(x) for x in pattern.split('_')[1:3])
    period = on + off
    if fit:
        n = max(1, round(length / period))
        k = length / (n * period)
        on, off, period = on * k, off * k, period * k
    out, s = [], off / 2
    while s < length - 1e-9:
        out.append((s, min(s + on, length)))
        s += period
    return [(a, b) for a, b in out if b - a > 0.05]


def _masks(tpl: Template, j: int, part: Part, seg: Segment, lane_weight: bool) -> tuple[int, int, int, int]:
    """Geometry-derived mask (spec §5.2): R wetness, G grime, B edge blend, A edge wear / lane weight."""
    t = tpl.columns[j].t
    def near(lines, radius):
        d = min((abs(t - x) for x in lines if (x < 0) == (t < 0) or abs(x) < 1e-9), default=1e9)
        return max(0.0, 1.0 - d / radius)
    r = g = b = a = 0.0
    if part in PAVED:
        r = 0.9 * near(tpl.flow_lines, 0.6)
        g = 0.15 + 0.6 * near(tpl.curb_toes, 1.0)
    if part == Part.DITCH:
        r = 1.0
    if part in (Part.CURB_FACE, Part.CURB_ARRIS, Part.CURB_TOP):
        g = 0.15
        a = 1.0 if (part == Part.CURB_ARRIS or 'top_front' in tpl.columns[j].tag) else 0.0
    if part == Part.SIDEWALK and 'back' in tpl.columns[j].tag:
        g = 0.3
    if part in PAVED | UNPAVED:
        edges = [c.t for k, c in enumerate(tpl.columns) if 0 < k < len(tpl.columns) - 1 and
                 (tpl.segments[k - 1].part in PAVED) != (tpl.segments[k].part in PAVED) and
                 {tpl.segments[k - 1].part, tpl.segments[k].part} & UNPAVED]
        b = near(edges, 0.25)
    if part in (Part.LANE, Part.SHOULDER, Part.MEDIAN_FLUSH) and lane_weight:
        a = 1.0
    return tuple(int(round(255 * max(0.0, min(1.0, x)))) for x in (r, g, b, a))


def sweep_range(tpl: Template, grid: _Grid, i0: int, i1: int, origin: tuple, opts: RoadOptions,
                name: str, open_start: bool, open_end: bool, drive_side: str) -> QMesh:
    """Build the mesh for loops i0..i1 (inclusive) of a global grid, in coordinates relative to origin."""
    m = QMesh(name)
    cols = tpl.columns; segs = tpl.segments
    ox, oy, oz = origin
    loops = range(i0, i1 + 1)
    vid = {(i, j): m.add_vert((grid.pos[i][j][0] - ox, grid.pos[i][j][1] - oy, grid.pos[i][j][2] - oz))
           for i in loops for j in range(len(cols))}
    for (i, j), v in vid.items():
        if i in (i0, i1):
            m.vtags[v] = f'port:{"Start" if i == i0 else "End"} col:{j}'
    pd = tpl.profile_distance()
    # Island groups: a new UV island at every hard column and every slot change.
    island, group = [], 0
    for j, sg in enumerate(segs):
        if j and (cols[j].hard or segs[j - 1].slot != sg.slot):
            group += 1
        island.append(group)
    flips: dict[str, int] = {}
    face_seg: list[int] = []
    lane_tile = 8.0

    def corner_uv(i: int, j: int, sg: Segment, world: tuple) -> tuple:
        u_m = grid.run[sg.ref][i]
        v_m = abs(pd[j] - pd[sg.anchor])
        rule = sg.uv
        if rule.kind == 'WORLD':
            uv1 = (world[0] / rule.tile, world[1] / rule.tile)
        elif rule.kind == 'PATH':
            uv1 = (u_m / rule.tile, v_m / rule.tile)
        else:
            sheet = uvlib.TRIM_SHEETS[rule.sheet]
            uv1 = (u_m / sheet.width_m, sheet.band_v(rule.band, v_m))
        return uv1, (u_m, v_m)

    for j, sg in enumerate(segs):
        for i in range(i0, i1):
            ids = (vid[(i, j)], vid[(i + 1, j)], vid[(i + 1, j + 1)], vid[(i, j + 1)])
            corners = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            uv1, par = [], []
            for (ci, cj) in corners:
                a, b = corner_uv(ci, cj, sg, grid.pos[ci][cj])
                uv1.append(a); par.append(b)
            # UV2_Lane: lane faces get a lane-aligned UV from the driver's right edge.
            lane = next((e for e in tpl.lane_edges if e[0] == sg.lane), None)
            if lane:
                _, lo, hi = lane
                side = -1 if hi <= 1e-9 else 1
                forward = (side < 0) == (drive_side == 'RHT')
                w = hi - lo
                uv2 = tuple(((1 if forward else -1) * p[0] / lane_tile,
                             ((cols[cj].t - lo) if forward else (hi - cols[cj].t)) / w)
                            for p, (_, cj) in zip(par, corners))
            else:
                uv2 = tuple(uv1)
            m.add_face(ids, sg.slot, sg.part, Kind.TOP, island[j],
                       {'UV1_Tile': tuple(uv1), 'UV2_Lane': uv2, '_PARAM': tuple(par)})
            face_seg.append(j)
            if sg.uv.kind == 'WORLD':
                m.meta.setdefault('world_faces', set()).add(len(m.faces) - 1)
            m.colors.setdefault(COLOR_MASK, []).append(tuple(_masks(tpl, cj, sg.part, sg, True) for _, cj in corners))
            flips.setdefault(sg.band, 0)
            flips[sg.band] += 1 if uvlib.signed_area(list(uv1)) >= 0 else -1
    # Reverse rule (spec E6): negate u only, per band, where the forward mapping is mirrored.
    for f, j in enumerate(face_seg):
        sg = segs[j]
        if sg.uv.kind != 'WORLD' and flips[sg.band] < 0:
            m.uv['UV1_Tile'][f] = tuple((-u, v) for u, v in m.uv['UV1_Tile'][f])
            m.uv['_PARAM'][f] = tuple((-u, v) for u, v in m.uv['_PARAM'][f])
            if sg.lane < 0:
                m.uv['UV2_Lane'][f] = m.uv['UV1_Tile'][f]
    # Hard columns → sharp + seam; island changes → seam.
    for j, c in enumerate(cols):
        if 0 < j < len(cols) - 1:
            hard = c.hard
            seam = hard or island[j - 1] != island[j]
            for i in range(i0, i1):
                if seam:
                    m.mark_edge(vid[(i, j)], vid[(i + 1, j)], sharp=hard, seam=True)
    if opts.skirt:
        _skirts(m, tpl, grid, vid, i0, i1, origin, open_start, open_end, island[-1] + 1)
    if opts.markings:
        _markings(m, tpl, grid, i0, i1, origin, opts)
    _finish_colors(m)
    return m


def _skirts(m: QMesh, tpl: Template, grid: _Grid, vid: dict, i0: int, i1: int, origin: tuple,
            open_start: bool, open_end: bool, island0: int) -> None:
    d = tpl.section.skirt_depth
    last = len(tpl.columns) - 1
    bottom: dict[tuple[int, int], int] = {}

    def bot(i, j):
        if (i, j) not in bottom:
            x, y, z = m.verts[vid[(i, j)]]
            bottom[(i, j)] = m.add_vert((x, y, z - d))
        return bottom[(i, j)]
    for side, j, seg in ((-1, 0, tpl.segments[0]), (1, last, tpl.segments[-1])):
        isl = island0 + (0 if side < 0 else 1)
        run = grid.run[j]
        for i in range(i0, i1):
            top_a, top_b = vid[(i, j)], vid[(i + 1, j)]
            if side < 0:
                ids = (top_a, bot(i, j), bot(i + 1, j), top_b)
                uvs = ((run[i], 0.0), (run[i], -d), (run[i + 1], -d), (run[i + 1], 0.0))
            else:
                ids = (top_a, top_b, bot(i + 1, j), bot(i, j))
                uvs = ((-run[i], 0.0), (-run[i + 1], 0.0), (-run[i + 1], -d), (-run[i], -d))
            uvs = tuple((u / 2.0, v / 2.0) for u, v in uvs)
            m.add_face(ids, seg.slot, Part.HIDDEN, Kind.SKIRT, isl, {'UV1_Tile': uvs, 'UV2_Lane': uvs,
                                                                     '_PARAM': tuple((u * 2, v * 2) for u, v in uvs)})
            m.colors.setdefault(COLOR_MASK, []).append(((0, 64, 0, 0),) * 4)
            m.mark_edge(top_a, top_b)
    # End curtains on free ends (T-ladder, one row high, sharing the skirt bottoms).
    for i, is_open, start in ((i0, open_start, True), (i1, open_end, False)):
        if is_open:
            continue
        isl = island0 + (2 if start else 3)
        for j in range(last):
            a, b = vid[(i, j)], vid[(i, j + 1)]
            pa, pb = m.verts[a], m.verts[b]
            ua, ub = tpl.columns[j].t, tpl.columns[j + 1].t
            if start:
                ids = (a, b, bot(i, j + 1), bot(i, j))
                uvs = ((-ua, pa[2]), (-ub, pb[2]), (-ub, pb[2] - d), (-ua, pa[2] - d))
            else:
                ids = (a, bot(i, j), bot(i, j + 1), b)
                uvs = ((ua, pa[2]), (ua, pa[2] - d), (ub, pb[2] - d), (ub, pb[2]))
            seg = tpl.segments[j]
            uvs = tuple((u / 2.0, v / 2.0) for u, v in uvs)
            m.add_face(ids, seg.slot, Part.CAP, Kind.CAP, isl, {'UV1_Tile': uvs, 'UV2_Lane': uvs,
                                                                '_PARAM': tuple((u * 2, v * 2) for u, v in uvs)})
            m.colors.setdefault(COLOR_MASK, []).append(((0, 64, 0, 0),) * 4)
            m.mark_edge(a, b)
        for j in (0, last):
            m.mark_edge(vid[(i, j)], bot(i, j))


def _markings(m: QMesh, tpl: Template, grid: _Grid, i0: int, i1: int, origin: tuple, opts: RoadOptions) -> None:
    """Raised marking shells: top quads on the surface + 3 mm, side walls sinking 2 mm into it."""
    st = grid.stations
    s0, s1 = st[i0], st[i1]
    length_total = st[-1]
    isl = max(m.face_island, default=0) + 10
    for t_c, spec in tpl.lines:
        for a, b in _dash_intervals(spec.pattern, length_total, opts.dash_period_fit):
            a, b = max(a, s0), min(b, s1)
            if b - a < 0.05:
                continue
            ss = [a] + [s for s in st[i0:i1 + 1] if a + 1e-6 < s < b - 1e-6] + [b]
            ts = [t_c - spec.width / 2, t_c + spec.width / 2]
            for c in tpl.columns:
                if ts[0] + 1e-4 < c.t < ts[-1] - 1e-4:
                    ts.insert(-1, c.t)
            _marking_shell(m, tpl, grid, ss, ts, origin, isl, spec)
            isl += 1


def _marking_shell(m: QMesh, tpl: Template, grid: _Grid, ss: list[float], ts: list[float], origin: tuple,
                   isl: int, spec) -> None:
    ox, oy, oz = origin
    st = grid.stations
    rows = []
    for s in ss:
        i = max(0, min(len(st) - 2, next((k for k in range(len(st) - 1) if st[k + 1] >= s - 1e-12), len(st) - 2)))
        k = (s - st[i]) / (st[i + 1] - st[i])
        row = []
        for t in ts:
            z = tpl.z_at(t)
            # Linear interpolation between the two loops at the same lateral offset matches the
            # triangulated surface along the loop direction exactly.
            pa = _lerp_col(grid, tpl, i, t, z); pb = _lerp_col(grid, tpl, i + 1, t, z)
            p = tuple(pa[c] + k * (pb[c] - pa[c]) for c in range(3))
            row.append(p)
        rows.append(row)
    top = [[m.add_vert((p[0] - ox, p[1] - oy, p[2] - oz + MARK_LIFT)) for p in row] for row in rows]
    low = [[m.add_vert((p[0] - ox, p[1] - oy, p[2] - oz - MARK_SINK)) for p in row] for row in rows]
    length = [0.0]
    for a, b in zip(rows, rows[1:]):
        length.append(length[-1] + math.dist(a[0], b[0]))
    w = ts[-1] - ts[0]
    def add(ids, uvs):
        uvs = tuple(uvs)
        m.add_face(ids, 'RD01_Marking', Part.MARKING, Kind.MARKING, isl,
                   {'UV1_Tile': uvs, 'UV2_Lane': uvs, '_PARAM': uvs})
        m.colors.setdefault(COLOR_MASK, []).append(((0, 30, 0, 0),) * len(ids))
    nr, nc = len(rows), len(ts)
    for r in range(nr - 1):
        for c in range(nc - 1):
            uv = [(length[r] / 2, (ts[c] - ts[0]) / w), (length[r + 1] / 2, (ts[c] - ts[0]) / w),
                  (length[r + 1] / 2, (ts[c + 1] - ts[0]) / w), (length[r] / 2, (ts[c + 1] - ts[0]) / w)]
            add((top[r][c], top[r + 1][c], top[r + 1][c + 1], top[r][c + 1]), uv)
    for r in range(nr - 1):          # long side walls
        a, b = length[r] / 2, length[r + 1] / 2
        add((top[r][0], low[r][0], low[r + 1][0], top[r + 1][0]), [(a, 0), (a, -.005), (b, -.005), (b, 0)])
        add((top[r][-1], top[r + 1][-1], low[r + 1][-1], low[r][-1]), [(-a, 0), (-b, 0), (-b, -.005), (-a, -.005)])
    for c in range(nc - 1):          # dash ends
        add((top[0][c], top[0][c + 1], low[0][c + 1], low[0][c]), [((ts[c] - ts[0]), 0), ((ts[c + 1] - ts[0]), 0), ((ts[c + 1] - ts[0]), -.005), ((ts[c] - ts[0]), -.005)])
        add((top[-1][c], low[-1][c], low[-1][c + 1], top[-1][c + 1]), [(-(ts[c] - ts[0]), 0), (-(ts[c] - ts[0]), -.005), (-(ts[c + 1] - ts[0]), -.005), (-(ts[c + 1] - ts[0]), 0)])
    ring = [top[0][c] for c in range(nc)] + [top[r][-1] for r in range(1, nr)] + \
           [top[-1][c] for c in range(nc - 2, -1, -1)] + [top[r][0] for r in range(nr - 2, 0, -1)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        m.mark_edge(a, b)
    for r in (0, nr - 1):
        for c in (0, nc - 1):
            m.mark_edge(top[r][c], low[r][c])


def _lerp_col(grid: _Grid, tpl: Template, i: int, t: float, z: float) -> tuple:
    """Point at lateral t on loop i, interpolated between the two template columns around t."""
    cols = tpl.columns
    for j in range(len(cols) - 1):
        if cols[j].t <= t <= cols[j + 1].t:
            k = (t - cols[j].t) / (cols[j + 1].t - cols[j].t)
            a, b = grid.pos[i][j], grid.pos[i][j + 1]
            return tuple(a[c] + k * (b[c] - a[c]) for c in range(3))
    raise ValueError(f'Marking at t={t:.3f} lies outside the cross-section.')


def _finish_colors(m: QMesh) -> None:
    m.colors[COLOR_ID] = [tuple(ID_COLOURS[Part(m.face_part[f])] + (255,) for _ in vids)
                          for f, vids in enumerate(m.faces)]
    m.colors[COLOR_MASK] = list(m.colors[COLOR_MASK])
    # Reverse rule for skirts, curtains and marking walls: negate u only where the mapping is mirrored.
    for f, kind in enumerate(m.face_kind):
        if kind != Kind.TOP:
            for layer in ('UV1_Tile', 'UV2_Lane', '_PARAM'):
                row = m.uv[layer][f]
                if uvlib.signed_area(list(row)) < 0:
                    m.uv[layer][f] = tuple((-u, v) for u, v in row)
    m.uv['UV0_Main'] = list(m.uv['UV1_Tile'])            # TILING pieces: UV0 = UV1 (spec D7)
    for layer in ('UV1_Tile', 'UV2_Lane', 'UV0_Main'):
        uvlib.rebase(m, layer)
    m.check_buffers()


def build_road(rail: Rail, tpl: Template, opts: RoadOptions | None = None) -> list[Piece]:
    """Sweep the whole road once, then split into chunks with duplicated boundary loops."""
    opts = opts or RoadOptions()
    check_offset(rail, tpl.reach)
    stations = sample_stations(rail, tpl.reach, opts.max_step, opts.sag_tol, opts.uniform)
    grid = _build_grid(rail, tpl, stations)
    L = rail.length
    n_chunks = 1 if opts.chunk_length <= 0 else max(1, round(L / opts.chunk_length))
    bounds = [0]
    for c in range(1, n_chunks):
        target = L * c / n_chunks
        bounds.append(min(range(len(stations)), key=lambda i: abs(stations[i] - target)))
    bounds.append(len(stations) - 1)
    bounds = sorted(set(bounds))
    pieces = []
    for c, (i0, i1) in enumerate(zip(bounds, bounds[1:])):
        centre = rail.at(stations[i0])
        name = opts.name if len(bounds) == 2 else f'{opts.name}_C{c:02d}'
        mesh = sweep_range(tpl, grid, i0, i1, centre, opts, name,
                           open_start=opts.port_start or i0 > 0, open_end=opts.port_end or i1 < len(stations) - 1,
                           drive_side=tpl.section.drive_side)
        heading_a = math.degrees(math.atan2(grid.tangent[i0][1], grid.tangent[i0][0]))
        heading_b = math.degrees(math.atan2(grid.tangent[i1][1], grid.tangent[i1][0]))
        end = rail.at(stations[i1])
        sockets = [Socket('Start', (0.0, 0.0, 0.0), (heading_a + 180.0) % 360.0),
                   Socket('End', (end[0] - centre[0], end[1] - centre[1], end[2] - centre[2]), heading_b % 360.0)]
        pieces.append(Piece(name, mesh, centre, 0.0, sockets, {
            'section': tpl.section.name, 'section_hash': tpl.section.section_hash(), 'region': tpl.section.region,
            's_range': (stations[i0], stations[i1]), 'uv_mode': 'TILING', 'stations': i1 - i0 + 1}))
    return pieces
