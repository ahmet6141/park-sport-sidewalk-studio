"""PK01 FLOW sidewalks: path-following paving, swept profiled curbs and rounded junctions.

The vendored SW01 1.0.1 core is used unchanged for its Path, prism, clipping and
material contract; this module only adds a second layout strategy on top of it:

* pavers are laid in courses that follow the centre line (curved pavers on bends,
  symmetric edge cuts, no slivers at module ends) instead of a world-aligned grid;
* curbs are profile sweeps (bullnose / chamfer / square) cut into jointed stones
  that bend with the path;
* junctions receive curb returns (concave fillets) and rounded dead ends instead
  of square pads.

Output keeps SW01 material slots, UV0 tiling, SW01_Tint colours, port metadata and
convex collision hulls, so Blender instancing, the bridge and the UE exporter are
unchanged. Visual scenery, not civil or accessibility engineering.
"""
from __future__ import annotations
from dataclasses import asdict
import math, random
from .vendor import sw01_core as sw
from .geometry import Mesh
from . import modeling, curves

PAVED_PATTERNS = ('RUNNING', 'STACK', 'SLABS')
DIRECTIONS = {'E': (1., 0.), 'N': (0., 1.), 'W': (-1., 0.), 'S': (0., -1.)}
ORDER = ('E', 'N', 'W', 'S')


def make_path(points, start_tangent=None, end_tangent=None):
    """sw.Path whose end cuts are exactly perpendicular to the design tangents.
    Sampled curves otherwise inherit a chord error at their ends, which would leave a
    hairline wedge against a junction mouth or a neighbouring module.
    """
    path = sw.Path(points)
    for index, tangent in ((0, start_tangent), (-1, end_tangent)):
        if tangent is not None:
            t = sw.unit(tangent)
            if sw.dot(t, path.tangents[index]) < math.cos(math.radians(8)):
                raise ValueError('Design tangent disagrees with the sampled curve end.')
            path.normals[index] = (-t[1], t[0])
    return path


def _normal_at(path, s):
    a = path.sample(s, 0.); b = path.sample(s, 1.)
    return (b[0]-a[0], b[1]-a[1])


def _stations(path, s0, s1):
    return [s0]+[s for s in path.dist if s0+1e-6 < s < s1-1e-6]+[s1]


def _even_breaks(length, pitch):
    num = max(1, int(math.ceil(length/pitch-1e-9)))
    return [length*k/num for k in range(num+1)]


def _lateral_courses(a, b, pitch):
    """Symmetric lateral courses: full units in the middle, equal cuts (>= half a unit) at both edges."""
    width = b-a
    if width <= 1e-6: return []
    n = int(math.floor(width/pitch+1e-6))
    rest = width-n*pitch
    if n == 0: widths = [width]
    elif rest <= 1e-4: widths = [pitch]*n
    else:
        edge = (pitch+rest)/2
        widths = [edge]+[pitch]*(n-1)+[edge]
    out = []; x = a
    for w in widths: out.append((x, x+w)); x += w
    out[-1] = (out[-1][0], b)
    return out


def _longitudinal(length, unit, offset, min_piece):
    """Break stations along a course, dropping slivers shorter than min_piece at the ends."""
    cuts = []
    k = math.floor(-offset/unit)-1
    while True:
        s = k*unit+offset; k += 1
        if s >= length: break
        if s > min_piece and length-s > min_piece: cuts.append(s)
    return [0.]+cuts+[length]


def _curb_stones(mesh, path, a, b, u_outer, u_inner, cfg, style, rng, elev, label):
    """Jointed curb stones swept along [a, b] of the path; stone length follows curvature."""
    profile, smooth = modeling.curb_profile(u_outer, u_inner, -cfg.base_depth, cfg.height, style,
                                            radius=min(.04, cfg.height*.25), chamfer=max(.004, cfg.curb_bevel))
    length = b-a
    # Radial stones: shorter units on tight bends, like a real curved kerb.
    turn = 0.
    for i in range(1, len(path.points)-1):
        if a < path.dist[i] < b: turn += abs(curves.turn_angle(path.points[i-1], path.points[i], path.points[i+1]))
    radius = length/turn if turn > 1e-6 else float('inf')
    pitch = cfg.curb_length if radius > 12 else max(.30, min(cfg.curb_length, radius*.12))
    breaks = _even_breaks(length, pitch)
    for s0, s1 in zip(breaks, breaks[1:]):
        s0 = a+s0+cfg.joint/2; s1 = a+s1-cfg.joint/2
        if s1-s0 < .05: continue
        st = _stations(path, s0, s1)
        rail = [path.sample(s, 0.) for s in st]; normals = [_normal_at(path, s) for s in st]
        var = rng.uniform(1-cfg.variation, 1+cfg.variation)
        tint = tuple(min(1., max(.04, v*var)) for v in cfg.curb_tint)
        modeling.sweep(mesh, rail, normals, profile, 2, smooth, [elev(s) for s in st], tint, cfg.texture_metres, label=label)


def _collision(path, cfg, half, max_turn=math.radians(6), max_len=12.):
    hulls = []; start = 0; turn = 0.
    for i in range(1, len(path.points)):
        if i < len(path.points)-1:
            turn += abs(curves.turn_angle(path.points[i-1], path.points[i], path.points[i+1]))
        last = i == len(path.points)-1
        if last or turn > max_turn or path.dist[i]-path.dist[start] > max_len:
            hulls.append({'polygon': path.strip(path.dist[start], path.dist[i], -half, half), 'z0': -cfg.base_depth,
                          'z1': cfg.height, 'end_elevation': cfg.end_elevation})
            start = i; turn = 0.
    return hulls


def build_flow_module(name, path, cfg, curb_style='BULLNOSE', min_piece=.12):
    """Drop-in alternative to sw.build_module: same inputs, same metadata contract."""
    cfg.validate()
    if curb_style not in modeling.CURB_STYLES: raise ValueError('Unknown curb profile.')
    mesh = Mesh(name); rng = random.Random(cfg.seed)
    L = path.length; half = cfg.width/2
    left = half-(cfg.curb_width if cfg.curb_left else 0.); right = -half+(cfg.curb_width if cfg.curb_right else 0.)
    fp = path.strip(0, L, -half, half)
    if not sw.simple_polygon(fp): raise ValueError('Offset footprint intersects itself. Widen the bend radius or reduce width.')
    if any(sw.length(n) > 2.65 for n in path.normals): raise ValueError('Miter ratio too large.')
    grade = cfg.end_elevation/L if L > 0 else 0.
    elev_s = (lambda s: grade*s) if cfg.end_elevation else (lambda s: 0.)
    elev_p = (lambda p: cfg.end_elevation*path.projection(p)/L) if cfg.end_elevation else None

    def prism(poly, z0, z1, mat, tint=(1., 1., 1.), bevel=0., label=''):
        var = rng.uniform(1-cfg.variation, 1+cfg.variation) if mat in (1, 2, 3) else 1.
        return mesh.prism(poly, z0, z1, mat, tuple(min(1., max(.04, v*var)) for v in tint), bevel, cfg.texture_metres,
                          (rng.uniform(0, 7), rng.uniform(0, 7)), label, elev_p)

    # Mortar bed between the curbs, stopping below the pavers (no coplanar faces).
    prism(path.strip(0, L, right, left), -cfg.base_depth, cfg.height-cfg.paver_thickness-.004, 0, label='bed')
    if cfg.curb_right: _curb_stones(mesh, path, 0., L, -half, right, cfg, curb_style, rng, elev_s, 'curb_R')
    if cfg.curb_left: _curb_stones(mesh, path, 0., L, half, left, cfg, curb_style, rng, elev_s, 'curb_L')
    pright, pleft = right+cfg.border_width, left-cfg.border_width
    if cfg.border_width > 0:
        breaks = _even_breaks(L, .40)
        for a, b in ((right, pright), (pleft, left)):
            for s0, s1 in zip(breaks, breaks[1:]):
                prism(path.strip(s0+cfg.joint/2, s1-cfg.joint/2, a+cfg.joint/2, b-cfg.joint/2),
                      cfg.height-cfg.paver_thickness, cfg.height, 3, cfg.border_tint, cfg.bevel, 'border')
    bands = [(pright, pleft)]
    if cfg.tactile:
        tr = cfg.tactile_offset-cfg.tactile_width/2; tl = cfg.tactile_offset+cfg.tactile_width/2
        bands = [(pright, tr-cfg.joint/2), (tl+cfg.joint/2, pleft)]
        breaks = _even_breaks(L, cfg.tactile_pitch)
        for s0, s1 in zip(breaks, breaks[1:]):
            prism(path.strip(s0+cfg.joint/2, s1-cfg.joint/2, tr, tl), cfg.height-cfg.paver_thickness, cfg.height, 4,
                  bevel=.002, label='tactile_tile')
            for k in range(4):
                off = tr+.055+k*(cfg.tactile_width-.11)/3
                if s1-s0 > .1:
                    prism(path.strip(s0+.04, s1-.04, off-.0095, off+.0095), cfg.height, cfg.height+cfg.tactile_relief, 4,
                          bevel=.0015, label='tactile_rib')
    count = 0; cut_area = 0.
    for a, b in bands:
        if b-a <= cfg.joint: continue
        if cfg.pattern in PAVED_PATTERNS:
            pl, pw = cfg.paver_length, cfg.paver_width
            if cfg.pattern == 'SLABS': pl = max(.60, pl); pw = max(.40, pw)
            for column, (o0, o1) in enumerate(_lateral_courses(a, b, pw)):
                offset = pl/2 if (column % 2 and cfg.pattern != 'STACK') else 0.
                stations = _longitudinal(L, pl, offset, min_piece)
                for s0, s1 in zip(stations, stations[1:]):
                    poly = path.strip(s0+cfg.joint/2, s1-cfg.joint/2, o0+cfg.joint/2, o1-cfg.joint/2)
                    if not poly: continue
                    count += 1
                    if count > cfg.max_pavers: raise ValueError(f'Safety limit of {cfg.max_pavers} pavers exceeded. Split the path.')
                    prism(poly, cfg.height-cfg.paver_thickness, cfg.height, 1, cfg.paver_tint, cfg.bevel, 'paver')
        else:
            domain = path.strip(cfg.joint/2, L-cfg.joint/2, a+cfg.joint/2, b-cfg.joint/2)
            c, area = _pattern_fill(mesh, domain, cfg, prism, count)
            count = c; cut_area += area
    if cut_area > 0: mesh.warnings.append(f'{cut_area:.6f} m² of sub-threshold edge slivers omitted.')
    n0 = sw.unit(path.normals[0]); n1 = sw.unit(path.normals[-1]); t0 = (n0[1], -n0[0]); t1 = (n1[1], -n1[0])
    meta = {'name': name, 'builder': 'PK01_FLOW', 'curb_profile': curb_style, 'config': asdict(cfg), 'length_m': L,
            'pavers': count, 'vertices': len(mesh.vertices), 'triangles': len(mesh.triangles), 'solids': len(mesh.solids),
            'path': path.points, 'warnings': mesh.warnings,
            'in': {'location': [path.points[0][0], path.points[0][1], 0.], 'yaw_degrees': math.degrees(math.atan2(t0[1], t0[0]))},
            'out': {'location': [path.points[-1][0], path.points[-1][1], cfg.end_elevation], 'yaw_degrees': math.degrees(math.atan2(t1[1], t1[0]))},
            'collision': _collision(path, cfg, half)}
    mesh.meta = {'sw01': meta}
    return mesh, meta


def _pattern_fill(mesh, domain, cfg, prism, count):
    """World-grid SW01 patterns (herringbone / basket / any pattern on junction pads)."""
    domain = sw.clean_polygon(domain)
    if not domain: return count, 0.
    tris = sw.triangulate(domain); cut_area = 0.
    bounds = (min(x for x, y in domain), min(y for x, y in domain), max(x for x, y in domain), max(y for x, y in domain))
    for rect in sw.tile_rectangles(bounds, cfg):
        for piece in sw.clip_regions(domain, rect, tris):
            if sw.area(piece) < cfg.min_cut_area: cut_area += sw.area(piece); continue
            count += 1
            if count > cfg.max_pavers: raise ValueError(f'Safety limit of {cfg.max_pavers} pavers exceeded.')
            prism(piece, cfg.height-cfg.paver_thickness, cfg.height, 1, cfg.paver_tint, cfg.bevel, 'paver')
    return count, cut_area


# ---------------------------------------------------------------- junctions

def junction_outline(arms, half, reach, fillet, end_radius, step=.18):
    """CCW outer outline of a junction and a per-edge flag list ('mouth' or 'curb').
    arms: subset of 'ENWS'. Concave corners get curb-return fillets, exposed convex
    corners get end_radius (half gives a semicircular dead end). Mouth corners stay sharp.
    """
    arms = [d for d in ORDER if d in set(arms)]
    pts = []; kinds = []  # kinds per vertex: 'mouth', 'concave', 'convex'
    for i, d in enumerate(ORDER):
        dx, dy = DIRECTIONS[d]; px, py = -dy, dx
        nxt = ORDER[(i+1) % 4]
        if d in arms:
            pts += [(dx*reach-px*half, dy*reach-py*half), (dx*reach+px*half, dy*reach+py*half)]; kinds += ['mouth', 'mouth']
        else:
            pts += [(dx*half-px*half, dy*half-py*half), (dx*half+px*half, dy*half+py*half)]; kinds += ['convex', 'convex']
        if d in arms and nxt in arms:
            pts.append((dx*half+px*half, dy*half+py*half)); kinds.append('concave')
    # Merge coincident vertices and drop collinear ones.
    merged = []
    for p, k in zip(pts, kinds):
        if merged and math.dist(p, merged[-1][0]) < 1e-9:
            if merged[-1][1] != 'mouth': merged[-1] = (p, k if k == 'mouth' else merged[-1][1])
            continue
        merged.append((p, k))
    if len(merged) > 1 and math.dist(merged[0][0], merged[-1][0]) < 1e-9: merged.pop()
    clean = []
    for i, (p, k) in enumerate(merged):
        a = merged[i-1][0]; c = merged[(i+1) % len(merged)][0]
        if k != 'mouth' and abs(sw.cross(sw.sub(p, a), sw.sub(c, p))) < 1e-9: continue
        clean.append((p, k))
    # Classify turn direction exactly and round the corners.
    out = []; flags = []
    n = len(clean)
    mouth_edges = set()
    for i in range(n):
        if clean[i][1] == 'mouth' and clean[(i+1) % n][1] == 'mouth':
            a, b = clean[i][0], clean[(i+1) % n][0]
            # A mouth edge spans the full width across an arm end.
            if abs(math.dist(a, b)-2*half) < 1e-6 and abs(max(abs(a[0]), abs(a[1]))-reach) < 1e-6: mouth_edges.add(i)
    vertex_runs = []
    for i in range(n):
        p, k = clean[i]; a = clean[i-1][0]; c = clean[(i+1) % n][0]
        turn = sw.cross(sw.sub(p, a), sw.sub(c, p))
        r = 0.
        if k != 'mouth': r = end_radius if turn > 0 else fillet
        if r > .05:
            u = sw.unit(sw.sub(a, p)); v = sw.unit(sw.sub(c, p))
            ang = math.acos(max(-1., min(1., sw.dot(u, v)))); halfang = ang/2
            r = min(r, .999*min(math.dist(a, p)*(1 if clean[i-1][1] == 'mouth' else .5),
                                math.dist(c, p)*(1 if clean[(i+1) % n][1] == 'mouth' else .5))*math.tan(halfang))
            trim = r/math.tan(halfang)
            p0 = sw.add(p, sw.mul(u, trim)); p1 = sw.add(p, sw.mul(v, trim))
            bis = sw.unit(sw.add(u, v)); centre = sw.add(p, sw.mul(bis, r/math.sin(halfang)))
            a0 = math.atan2(p0[1]-centre[1], p0[0]-centre[0]); a1 = math.atan2(p1[1]-centre[1], p1[0]-centre[0])
            sweep_ = (a1-a0+math.pi) % math.tau-math.pi
            steps = max(3, math.ceil(abs(sweep_)*r/step))
            vertex_runs.append([(centre[0]+r*math.cos(a0+sweep_*t/steps), centre[1]+r*math.sin(a0+sweep_*t/steps)) for t in range(steps+1)])
        else:
            vertex_runs.append([p])
    for i, run in enumerate(vertex_runs):
        for j, q in enumerate(run):
            out.append(q)
            last = j == len(run)-1
            flags.append('mouth' if (last and i in mouth_edges) else 'curb')
    return out, flags


def build_junction(name, arms, cfg, reach, fillet=2.5, end_radius=None, curb_style='BULLNOSE'):
    """Rounded junction pad: world-grid paving, curb returns, open mouths flush with arms."""
    cfg.validate(); half = cfg.width/2
    end_radius = half-.01 if end_radius is None else end_radius
    if arms and reach < half+.05: raise ValueError('Junction reach must exceed half the path width.')
    outline, flags = junction_outline(arms, half, reach, fillet, end_radius)
    mesh = Mesh(name); rng = random.Random(cfg.seed)

    def prism(poly, z0, z1, mat, tint=(1., 1., 1.), bevel=0., label=''):
        var = rng.uniform(1-cfg.variation, 1+cfg.variation) if mat in (1, 2, 3) else 1.
        return mesh.prism(poly, z0, z1, mat, tuple(min(1., max(.04, v*var)) for v in tint), bevel, cfg.texture_metres,
                          (rng.uniform(0, 7), rng.uniform(0, 7)), label)

    cw = cfg.curb_width
    inner = curves.offset_polygon(outline, [cw if f == 'curb' else 0. for f in flags])
    prism(inner, -cfg.base_depth, cfg.height-cfg.paver_thickness-.004, 0, label='bed')
    bw = cfg.border_width
    domain = curves.offset_polygon(outline, [cw+bw+cfg.joint/2 if f == 'curb' else cfg.joint/2 for f in flags])
    count, _ = _pattern_fill(mesh, domain, cfg, prism, 0)
    # Curb runs: maximal chains of curb edges between mouths (or a closed ring).
    n = len(outline); runs = []
    if 'mouth' not in flags:
        runs.append(outline+[outline[0]])
    else:
        i0 = flags.index('mouth')
        run = None
        for k in range(1, n+1):
            i = (i0+k) % n
            if flags[i] == 'curb':
                if run is None: run = [outline[i]]
                run.append(outline[(i+1) % n])
            elif run is not None:
                runs.append(run); run = None
        if run is not None: runs.append(run)
    profile, smooth = modeling.curb_profile(0., cw, -cfg.base_depth, cfg.height, curb_style,
                                            radius=min(.04, cfg.height*.25), chamfer=max(.004, cfg.curb_bevel))
    for run in runs:
        closed = math.dist(run[0], run[-1]) < 1e-9
        pts = run[:-1] if closed else run
        if closed:
            # Break a closed ring at the first vertex; ends meet with a joint.
            pts = pts+[pts[0]]
        path = sw.Path(pts)
        if closed:
            # A closed ring must use the true miter at its seam.
            t_in = sw.unit(sw.sub(pts[-1], pts[-2])); t_out = sw.unit(sw.sub(pts[1], pts[0]))
            nn = sw.add((-t_in[1], t_in[0]), (-t_out[1], t_out[0])); nn = sw.mul(nn, 1/(1+sw.dot((-t_in[1], t_in[0]), (-t_out[1], t_out[0]))))
            path.normals[0] = nn; path.normals[-1] = nn
        breaks = _even_breaks(path.length, cfg.curb_length if path.length > 3 else max(.3, path.length/3))
        for s0, s1 in zip(breaks, breaks[1:]):
            a = s0+cfg.joint/2; b = s1-cfg.joint/2
            if b-a < .05: continue
            st = _stations(path, a, b)
            var = rng.uniform(1-cfg.variation, 1+cfg.variation)
            tint = tuple(min(1., max(.04, v*var)) for v in cfg.curb_tint)
            modeling.sweep(mesh, [path.sample(s, 0.) for s in st], [_normal_at(path, s) for s in st], profile, 2,
                           smooth, None, tint, cfg.texture_metres, label='curb_return')
        if bw > 0:
            # Soldier border continues the arms' border strips around the curb return.
            border_breaks = _even_breaks(path.length, .40)
            for s0, s1 in zip(border_breaks, border_breaks[1:]):
                poly = path.strip(s0+cfg.joint/2, s1-cfg.joint/2, cw+cfg.joint/2, cw+bw-cfg.joint/2)
                if poly: prism(poly, cfg.height-cfg.paver_thickness, cfg.height, 3, cfg.border_tint, cfg.bevel, 'border')
    # Convex collision: centre square, arm rectangles and fillet wedges.
    hulls = [{'polygon': [(-half, -half), (half, -half), (half, half), (-half, half)], 'z0': -cfg.base_depth, 'z1': cfg.height, 'end_elevation': 0.}]
    for d in arms:
        dx, dy = DIRECTIONS[d]; px, py = -dy, dx
        poly = [(dx*half-px*half, dy*half-py*half), (dx*reach-px*half, dy*reach-py*half),
                (dx*reach+px*half, dy*reach+py*half), (dx*half+px*half, dy*half+py*half)]
        if sw.area(poly) < 0: poly.reverse()
        hulls.append({'polygon': poly, 'z0': -cfg.base_depth, 'z1': cfg.height, 'end_elevation': 0.})
    r = min(fillet, .999*(reach-half))
    if r > .05:
        for i, d in enumerate(ORDER):
            nxt = ORDER[(i+1) % 4]
            if d not in arms or nxt not in arms: continue
            dx, dy = DIRECTIONS[d]; px, py = DIRECTIONS[nxt]
            c = (dx*half+px*half, dy*half+py*half); t1 = (c[0]+dx*r, c[1]+dy*r); t2 = (c[0]+px*r, c[1]+py*r)
            k = r*(1-1/math.sqrt(2)); mid = (c[0]+(dx+px)*k, c[1]+(dy+py)*k)
            # Two convex wedges hug the curb-return arc instead of one oversized triangle.
            for poly in ([c, t1, mid], [c, mid, t2]):
                if sw.area(poly) < 0: poly.reverse()
                hulls.append({'polygon': poly, 'z0': -cfg.base_depth, 'z1': cfg.height, 'end_elevation': 0.})
    meta = {'name': name, 'builder': 'PK01_FLOW_JUNCTION', 'arms': list(arms), 'reach_m': reach, 'fillet_m': fillet,
            'curb_profile': curb_style, 'config': asdict(cfg), 'length_m': 2*half, 'pavers': count,
            'vertices': len(mesh.vertices), 'triangles': len(mesh.triangles), 'solids': len(mesh.solids),
            'path': [(-half, 0.), (half, 0.)], 'outline': outline, 'warnings': mesh.warnings,
            'in': {'location': [-half, 0., 0.], 'yaw_degrees': 0.}, 'out': {'location': [half, 0., 0.], 'yaw_degrees': 0.},
            'collision': hulls}
    mesh.meta = {'sw01': meta}
    return mesh, meta
