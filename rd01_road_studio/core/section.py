"""Cross-section bands and their compilation into a lateral profile template (spec §2).

A road is described from the centre outward on each side by ordered bands (lane, gutter,
curb, sidewalk, verge, shoulder, bankett, embankment, ditch, median). `compile_section`
turns that into a `Template`: strictly increasing lateral columns t (metres, + = left),
their height z on the finished surface, hard/soft flags and one `Segment` per gap with
its material slot, surface part and UV rule. Pure Python, deterministic.
"""
from __future__ import annotations
from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import json
import math
from .qmesh import Part

ARRIS_MIN_DT = 0.002      # columns closer than 2 mm are merged / dropped (§2.3)
HARD_ANGLE_DEG = 30.0     # a profile break sharper than this is a hard (sharp + seam) column
DRAFT = 1.0 / 20.0        # near-vertical segments keep a 1:20 batter so TOP stays a height field


class BandKind(str, Enum):
    LANE = 'LANE'; SHOULDER_PAVED = 'SHOULDER_PAVED'; MEDIAN_FLUSH = 'MEDIAN_FLUSH'; GUTTER = 'GUTTER'
    CURB = 'CURB'; SIDEWALK = 'SIDEWALK'; VERGE = 'VERGE'; BANKETT = 'BANKETT'
    EMBANKMENT = 'EMBANKMENT'; DITCH = 'DITCH'


class CurbType(str, Enum):
    BARRIER = 'BARRIER'; MOUNTABLE = 'MOUNTABLE'; FLUSH = 'FLUSH'


@dataclass(frozen=True)
class LineSpec:
    """Longitudinal marking. `offset` is from the band's inner edge (m), `pattern` 'SOLID' or 'DASH_<on>_<off>'."""
    kind: str
    offset: float
    width: float = 0.12
    pattern: str = 'SOLID'
    colour: str = 'WHITE'


@dataclass(frozen=True)
class Band:
    kind: BandKind
    width: float = 0.0
    p: tuple[tuple[str, float | str], ...] = ()      # extra parameters as sorted (key, value) pairs
    lines: tuple[LineSpec, ...] = ()

    def get(self, key: str, default):
        return dict(self.p).get(key, default)


@dataclass(frozen=True)
class CrossSection:
    name: str
    region: str
    right: tuple[Band, ...]
    left: tuple[Band, ...]
    median: tuple[Band, ...] = ()
    crossfall: float = 0.025
    closure: str = 'SKIRT'
    skirt_depth: float = 0.5
    drive_side: str = 'RHT'
    centre_lines: tuple[LineSpec, ...] = ()

    def section_hash(self) -> str:
        def band(b: Band):
            return [b.kind.value, round(b.width, 6), list(b.p), [list(l.__dict__.values()) for l in b.lines]]
        data = [self.region, [band(b) for b in self.right], [band(b) for b in self.left],
                [band(b) for b in self.median], self.crossfall, self.closure, self.skirt_depth, self.drive_side,
                [list(l.__dict__.values()) for l in self.centre_lines]]
        return hashlib.blake2b(json.dumps(data).encode(), digest_size=8).hexdigest()

    def mirrored(self) -> 'CrossSection':
        return replace(self, right=self.left, left=self.right)


@dataclass(frozen=True)
class UVRule:
    """UV1 rule of a segment. WORLD: planar XY / tile; PATH: (run, profile) / tile; TRIM: trim-sheet band."""
    kind: str                          # 'WORLD' | 'PATH' | 'TRIM'
    tile: float = 4.0
    sheet: str = ''
    band: str = ''


@dataclass(frozen=True)
class Column:
    t: float
    z: float
    hard: bool
    tag: str
    side: int                          # -1 right, 0 centre/median, +1 left


@dataclass(frozen=True)
class Segment:
    """Surface between columns j and j+1."""
    part: Part
    slot: str
    uv: UVRule
    band: str                          # band id, e.g. 'R.curb'
    ref: int                           # column whose run length is the u of the whole band (radial joints)
    anchor: int                        # column where profile distance v = 0
    lane: int = -1                     # lane index for UV2_Lane (-1 = not a lane)
    wear: bool = False                 # edge-wear mask on this segment (curb arris / top front)


@dataclass(frozen=True)
class Template:
    columns: tuple[Column, ...]
    segments: tuple[Segment, ...]
    section: CrossSection
    lines: tuple[tuple[float, LineSpec], ...]       # (t of line centre, spec)
    lane_edges: tuple[tuple[int, float, float], ...]  # (lane id, t_lo, t_hi) for UV2_Lane
    flow_lines: tuple[float, ...]                   # t of gutter flow lines (wetness mask)
    curb_toes: tuple[float, ...]                    # t of curb toes (grime mask)

    @property
    def reach(self) -> float:
        return max(abs(c.t) for c in self.columns)

    def tag_index(self, tag: str) -> int:
        for j, c in enumerate(self.columns):
            if tag in c.tag.split():
                return j
        raise KeyError(tag)

    def z_at(self, t: float) -> float:
        """Surface height at lateral offset t (linear between columns)."""
        cols = self.columns
        if t <= cols[0].t:
            return cols[0].z
        for a, b in zip(cols, cols[1:]):
            if t <= b.t:
                k = (t - a.t) / (b.t - a.t)
                return a.z + k * (b.z - a.z)
        return cols[-1].z

    def profile_distance(self) -> list[float]:
        """Cumulative (t, z) distance from the first column."""
        out = [0.0]
        for a, b in zip(self.columns, self.columns[1:]):
            out.append(out[-1] + math.hypot(b.t - a.t, b.z - a.z))
        return out


# ------------------------------------------------------------------ emitters
SLOT = {
    'asphalt': 'RD01_Asphalt', 'curb': 'RD01_TrimCurb', 'gutter': 'RD01_TrimGutter', 'concrete': 'RD01_Concrete',
    'grass': 'RD01_Grass', 'gravel': 'RD01_Gravel', 'soil': 'RD01_Soil', 'marking': 'RD01_Marking',
}


class _Half:
    """Accumulates (t_abs, z, tag, hard_hint, segment_after) outward for one side."""

    def __init__(self, side: int, t0: float, z0: float, prefix: str):
        self.side, self.prefix = side, prefix
        self.pts: list[list] = [[t0, z0, '', None]]   # t is |t| here; [dist, z, tag, forced_soft]
        self.segs: list[dict] = []

    @property
    def t(self) -> float:
        return self.pts[-1][0]

    @property
    def z(self) -> float:
        return self.pts[-1][1]

    def tag_last(self, tag: str) -> None:
        self.pts[-1][2] = (self.pts[-1][2] + ' ' + self.prefix + tag).strip()

    def go(self, dt: float, dz: float, seg: dict, tag: str = '', soft: bool | None = None) -> None:
        if dt < ARRIS_MIN_DT:
            if dt < 0:
                raise ValueError('Profile must run outward.')
            # Below the merge tolerance: move the last point instead of adding one.
            self.pts[-1][0] += dt; self.pts[-1][1] += dz
            if tag:
                self.tag_last(tag)
            return
        self.segs.append(seg)
        self.pts.append([self.t + dt, self.z + dz, (self.prefix + tag) if tag else '', soft])

    def split(self, width: float, max_step: float, slope: float, seg: dict, end_tag: str, min_count: int = 1) -> None:
        n = max(min_count, math.ceil(width / max_step - 1e-9))
        for k in range(n):
            self.go(width / n, -slope * width / n, seg, end_tag if k == n - 1 else '')


def _seg(part: Part, slot: str, uv: UVRule, band: str, lane: int = -1, wear: bool = False) -> dict:
    return dict(part=part, slot=slot, uv=uv, band=band, lane=lane, wear=wear)


def _curb_points(kind: CurbType, reveal: float, top: float, setback: float, arris_r: float,
                 arris_seg: int, sw_cs: float) -> list[tuple[float, float, str, bool]]:
    """Curb outline from the toe as (dt, dz, tag, is_arris): face → rounded arris → top (rises at sw_cs)."""
    if kind == CurbType.MOUNTABLE:
        setback = max(setback, reveal); arris_r = max(arris_r, 0.025)
    if kind == CurbType.FLUSH:
        reveal = min(reveal, 0.03)
    setback = max(setback, reveal * DRAFT)
    r = min(arris_r, reveal / 2, top / 3)
    face = (setback, reveal)
    out: list[tuple[float, float, str, bool]] = []
    if r < 0.003:
        out.append((face[0], face[1], 'face_top', False))
        out.append((top, top * sw_cs, 'curb_back', False))
        return out
    # Fillet between the face line (direction d1) and the top line (direction d2).
    d1 = _unit(face); d2 = _unit((1.0, sw_cs))
    turn = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1])))
    trim = r * math.tan(turn / 2)
    p0 = (face[0] - d1[0] * trim, face[1] - d1[1] * trim)
    corner = face
    p1 = (corner[0] + d2[0] * trim, corner[1] + d2[1] * trim)
    inside = (d1[1], -d1[0])         # right of the upward face direction = inside the curb body
    centre = (p0[0] + inside[0] * r, p0[1] + inside[1] * r)
    a0 = math.atan2(p0[1] - centre[1], p0[0] - centre[0]); a1 = math.atan2(p1[1] - centre[1], p1[0] - centre[0])
    sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    pts = [p0] + [(centre[0] + r * math.cos(a0 + sweep * k / arris_seg), centre[1] + r * math.sin(a0 + sweep * k / arris_seg))
                  for k in range(1, arris_seg)] + [p1]
    prev = (0.0, 0.0)
    for k, p in enumerate(pts):
        tag = 'face_top' if k == 0 else ('top_front' if k == len(pts) - 1 else f'arris{k}')
        out.append((p[0] - prev[0], p[1] - prev[1], tag, 0 < k < len(pts) - 1))
        prev = p
    back = top + setback
    out.append((back - prev[0], (back - prev[0]) * sw_cs, 'curb_back', False))
    return out


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)


def _emit_half(h: _Half, bands: tuple[Band, ...], cs: CrossSection, lanes: list, lines: list,
               flows: list, toes: list) -> None:
    side = h.side
    for b_index, b in enumerate(bands):
        bid = f'{h.prefix}{b.kind.value.lower()}{b_index}'
        if b.kind in (BandKind.LANE, BandKind.MEDIAN_FLUSH, BandKind.SHOULDER_PAVED):
            slope = cs.crossfall if b.kind != BandKind.SHOULDER_PAVED else max(cs.crossfall, b.get('slope', 0.04))
            lane = len(lanes) if b.kind == BandKind.LANE else -1
            part = {BandKind.LANE: Part.LANE, BandKind.MEDIAN_FLUSH: Part.MEDIAN_FLUSH}.get(b.kind, Part.SHOULDER)
            t_in = h.t
            for ln in b.lines:
                lines.append((side * (t_in + ln.offset), ln))
            h.split(b.width, 1.75, slope, _seg(part, SLOT['asphalt'], UVRule('WORLD', 4.0), bid, lane),
                    'edge', min_count=2 if b.kind == BandKind.LANE else 1)
            if lane >= 0:
                lanes.append((lane, side, t_in, h.t))
        elif b.kind == BandKind.GUTTER:
            h.tag_last('lip')
            seg = _seg(Part.GUTTER, SLOT['gutter'], UVRule('TRIM', 2.0, 'RD01_TrimGutter', 'GUTTER'), bid)
            slope = float(b.get('slope', 0.06))
            if b.width < 0.3:
                h.go(b.width, -slope * b.width, seg, 'flow')
            else:
                h.go(b.width - 0.25, -slope * (b.width - 0.25), seg)
                h.go(0.25, -slope * 0.25, seg, 'flow')
            flows.append(side * h.t)
        elif b.kind == BandKind.CURB:
            kind = CurbType(b.get('type', 'BARRIER'))
            h.tag_last('toe')
            toes.append(side * h.t)
            pts = _curb_points(kind, float(b.get('reveal', 0.12)), float(b.get('top', 0.15)),
                               float(b.get('setback', 0.03)), float(b.get('arris_r', 0.012)),
                               int(b.get('arris_seg', 2)), float(b.get('sw_cs', 0.015)))
            uv = UVRule('TRIM', 2.0, 'RD01_TrimCurb', 'CURB')
            for k, (dt, dz, tag, is_arris) in enumerate(pts):
                part = Part.CURB_FACE if k == 0 else (Part.CURB_TOP if tag == 'curb_back' else Part.CURB_ARRIS)
                h.go(dt, dz, _seg(part, SLOT['curb'], uv, bid, wear=part == Part.CURB_ARRIS), tag,
                     soft=True if is_arris else None)
        elif b.kind == BandKind.SIDEWALK:
            sw_cs = float(b.get('slope', 0.015))
            h.split(b.width, 1.5, -sw_cs, _seg(Part.SIDEWALK, SLOT['concrete'], UVRule('PATH', 2.0), bid), 'back')
        elif b.kind in (BandKind.VERGE, BandKind.BANKETT):
            slope = float(b.get('slope', 0.04 if b.kind == BandKind.VERGE else 0.06))
            part, slot = (Part.VERGE, SLOT['grass']) if b.kind == BandKind.VERGE else (Part.GRAVEL, SLOT['gravel'])
            h.split(b.width, 1.0 if b.kind == BandKind.VERGE else 1.5, slope,
                    _seg(part, slot, UVRule('WORLD', 4.0), bid), 'outer')
        elif b.kind == BandKind.EMBANKMENT:
            height = float(b.get('height', 1.0)); ratio = float(b.get('ratio', 1.5))
            seg = _seg(Part.VERGE, SLOT['grass'], UVRule('PATH', 4.0), bid)
            h.tag_last('hinge')
            run = height * ratio
            if run <= 0.8:
                raise ValueError('Embankment too low for its rounded crest and toe.')
            # Rounded crest and toe (half-slope columns) so the slope reads as earthwork, not a fold.
            h.go(0.3, -0.15 / ratio, seg, 'crest')
            n = max(1, math.ceil((run - 0.6) / 1.0))
            for _ in range(n):
                h.go((run - 0.6) / n, -(height - 0.3 / ratio) / n, seg)
            h.go(0.3, -0.15 / ratio, seg, 'toe_e')
            h.go(1.0, -0.01, seg, 'apron')
        elif b.kind == BandKind.DITCH:
            depth = float(b.get('depth', 0.6)); ratio = float(b.get('ratio', 2.0)); bottom = float(b.get('bottom', 0.5))
            seg_g = _seg(Part.VERGE, SLOT['grass'], UVRule('PATH', 4.0), bid)
            seg_d = _seg(Part.DITCH, SLOT['soil'], UVRule('PATH', 4.0), bid)
            run = depth * ratio
            h.split(run, 1.0, depth / run, seg_g, 'ditch_in')
            h.go(bottom / 2, -0.03, seg_d, 'ditch_bottom')
            h.go(bottom / 2, 0.03, seg_d, 'ditch_out')
            flows.append(side * (h.t - bottom / 2))
            h.split(run, 1.0, -depth / run, seg_g, 'apron')
        else:
            raise ValueError(f'Band {b.kind} is not allowed on a road half.')


def compile_section(cs: CrossSection) -> Template:
    """Compile a cross-section into lateral columns and segments (right half mirrored to negative t)."""
    lanes: list = []; lines: list = []; flows: list = []; toes: list = []
    # Median: symmetric flat bands centred on t = 0, emitted as a left half and mirrored.
    med = _Half(+1, 0.0, 0.0, 'M.')
    if cs.median:
        _emit_half(med, tuple(replace(b, width=b.width / 2) for b in cs.median), cs, [], [], [], [])
    m_pts, m_segs = med.pts, med.segs
    halves = {}
    for side, bands, prefix in ((-1, cs.right, 'R.'), (+1, cs.left, 'L.')):
        h = _Half(side, m_pts[-1][0], m_pts[-1][1], prefix)
        _emit_half(h, bands, cs, lanes, lines, flows, toes)
        halves[side] = h
    for ln in cs.centre_lines:
        lines.append((ln.offset, ln))

    # Assemble columns: right half reversed (outermost first), median, left half.
    raw: list[tuple[float, float, str, bool | None]] = []
    segs: list[dict] = []
    r = halves[-1]
    for k in range(len(r.pts) - 1, 0, -1):
        p = r.pts[k]; raw.append((-p[0], p[1], p[2], p[3])); segs.append(r.segs[k - 1])
    mp = list(m_pts)
    for k in range(len(mp) - 1, 0, -1):
        raw.append((-mp[k][0], mp[k][1], ('M.' + mp[k][2]) if mp[k][2] else '', mp[k][3])); segs.append(m_segs[k - 1])
    raw.append((0.0, mp[0][1], 'crown', None))
    for k in range(1, len(mp)):
        segs.append(m_segs[k - 1]); raw.append((mp[k][0], mp[k][1], mp[k][2], mp[k][3]))
    l = halves[+1]
    for k in range(1, len(l.pts)):
        segs.append(l.segs[k - 1]); p = l.pts[k]; raw.append((p[0], p[1], p[2], p[3]))
    # Hard flags from the angle between neighbouring segments.
    columns = []
    for j, (t, z, tag, soft) in enumerate(raw):
        hard = False
        if 0 < j < len(raw) - 1 and soft is not True:
            a = (t - raw[j - 1][0], z - raw[j - 1][1]); b = (raw[j + 1][0] - t, raw[j + 1][1] - z)
            ang = math.degrees(abs(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])))
            hard = ang > HARD_ANGLE_DEG
        side = -1 if t < -1e-9 else (1 if t > 1e-9 else 0)
        columns.append(Column(t, z, hard, tag.strip(), side))
    for a, b in zip(columns, columns[1:]):
        if b.t - a.t < ARRIS_MIN_DT - 1e-12:
            raise ValueError(f'{cs.name}: columns {a.tag!r}/{b.tag!r} closer than 2 mm.')
    # Reference / anchor columns per band: the run is measured on the band's innermost (road-side) column.
    band_cols: dict[str, list[int]] = {}
    for j, s in enumerate(segs):
        band_cols.setdefault(s['band'], []).extend([j, j + 1])
    segments = []
    for j, s in enumerate(segs):
        cols = band_cols[s['band']]
        lo, hi = min(cols), max(cols)
        inner = hi if columns[lo].t < 0 and columns[hi].t <= 0 else lo
        if s['band'].startswith('M.'):
            inner = lo if columns[lo].t >= 0 else hi
        segments.append(Segment(s['part'], s['slot'], s['uv'], s['band'], inner, inner, s['lane'], s['wear']))
    lane_edges = tuple((lane, -t1 if side < 0 else t0, -t0 if side < 0 else t1) for lane, side, t0, t1 in lanes)
    return Template(tuple(columns), tuple(segments), cs, tuple(sorted(lines, key=lambda x: x[0])), lane_edges,
                    tuple(flows), tuple(toes))
