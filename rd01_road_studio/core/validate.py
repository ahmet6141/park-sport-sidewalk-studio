"""Topology / UV validator (spec §9.1). Returns issues instead of raising, so the UI can list them.

ERROR codes block export; WARN codes are reported. Checks:
NGON, TRI (outside documented poles), DEGENERATE, NONMANIFOLD, WINDING, TJUNCTION,
SHARP_NOT_SEAM, HEIGHTFIELD (TOP faces must face up, n_z ≥ 0.045), UV_FLIP (negative signed
UV area), UV_RANGE (UNIQUE UV0 outside 0–1), UV_OVERLAP (UNIQUE islands), UV_LARGE (|uv| > 24,
half-float precision in UE), NONFINITE.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from .qmesh import QMesh, Kind, UV_LAYERS, edge_key
from .uv import signed_area


@dataclass(frozen=True)
class Issue:
    level: str          # 'ERROR' | 'WARN'
    code: str
    message: str

    def __str__(self) -> str:
        return f'{self.level} {self.code}: {self.message}'


def _point_segment(p, a, b) -> tuple[float, float]:
    ab = tuple(b[i] - a[i] for i in range(3)); ap = tuple(p[i] - a[i] for i in range(3))
    ll = sum(c * c for c in ab)
    if ll < 1e-18:
        return 0.0, math.dist(p, a)
    k = sum(ap[i] * ab[i] for i in range(3)) / ll
    q = tuple(a[i] + k * ab[i] for i in range(3))
    return k, math.dist(p, q)


def validate_mesh(m: QMesh, uv_mode: str = 'TILING', tj_tol: float = 0.001) -> list[Issue]:
    issues: list[Issue] = []
    def err(code, msg): issues.append(Issue('ERROR', code, f'{m.name}: {msg}'))
    def warn(code, msg): issues.append(Issue('WARN', code, f'{m.name}: {msg}'))
    try:
        m.check_buffers()
    except AssertionError as e:
        err('BUFFERS', str(e))
        return issues
    if any(not math.isfinite(c) for p in m.verts for c in p):
        err('NONFINITE', 'non-finite vertex')
    poles = {v for v, tag in m.vtags.items() if 'pole:' in tag}
    for f, vids in enumerate(m.faces):
        if len(vids) > 4:
            err('NGON', f'face {f} has {len(vids)} corners')
        elif len(vids) == 3 and not poles & set(vids):
            err('TRI', f'face {f} is a triangle outside a documented pole')
        if m.face_area(f) < 1e-8 or any(math.dist(m.verts[a], m.verts[b]) < 0.0005
                                        for a, b in zip(vids, vids[1:] + vids[:1])):
            err('DEGENERATE', f'face {f} is degenerate (area or edge < 0.5 mm)')
        if m.face_kind[f] == Kind.TOP and m.face_normal(f)[2] < 0.045:
            err('HEIGHTFIELD', f'TOP face {f} is steeper than 1:20 or faces down (n_z={m.face_normal(f)[2]:.3f})')
    directed: dict[tuple[int, int], int] = {}
    for vids in m.faces:
        for a, b in zip(vids, vids[1:] + vids[:1]):
            directed[(a, b)] = directed.get((a, b), 0) + 1
    ef = m.edge_faces()
    for e, faces in ef.items():
        if len(faces) > 2:
            err('NONMANIFOLD', f'edge {e} is shared by {len(faces)} faces')
    if any(n > 1 for n in directed.values()):
        err('WINDING', 'two faces traverse the same edge in the same direction (flipped neighbour)')
    if not m.sharp <= m.seams:
        err('SHARP_NOT_SEAM', f'{len(m.sharp - m.seams)} hard edges are not UV seams')
    # T-junctions: a vertex lying on the interior of a boundary edge of its own component.
    boundary = [e for e, faces in ef.items() if len(faces) == 1]
    if boundary:
        comp_of = {}
        for c, faces in enumerate(m.components()):
            for f in faces:
                for v in m.faces[f]:
                    comp_of[v] = c
        cell = 0.25
        grid: dict[tuple, list[int]] = {}
        for v, p in enumerate(m.verts):
            grid.setdefault((int(p[0] // cell), int(p[1] // cell), int(p[2] // cell)), []).append(v)
        hits = 0
        for a, b in boundary:
            pa, pb = m.verts[a], m.verts[b]
            lo = [int(min(pa[i], pb[i]) // cell) - 1 for i in range(3)]
            hi = [int(max(pa[i], pb[i]) // cell) + 1 for i in range(3)]
            if (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2]) > 4000:
                continue
            for gx in range(lo[0], hi[0] + 1):
                for gy in range(lo[1], hi[1] + 1):
                    for gz in range(lo[2], hi[2] + 1):
                        for v in grid.get((gx, gy, gz), ()):
                            if v in (a, b) or comp_of.get(v) != comp_of.get(a):
                                continue
                            k, d = _point_segment(m.verts[v], pa, pb)
                            if 0.001 < k < 0.999 and d < tj_tol:
                                hits += 1
        if hits:
            err('TJUNCTION', f'{hits} vertices lie on open edges of their own component')
    for layer in UV_LAYERS:
        rows = m.uv.get(layer)
        if rows is None:
            err('UV_MISSING', f'layer {layer} missing')
            continue
        flipped = sum(1 for f, row in enumerate(rows) if signed_area(list(row)) < -1e-12)
        if flipped:
            err('UV_FLIP', f'{flipped} faces have negative UV area on {layer}')
        big = max((abs(c) for row in rows for uv in row for c in uv), default=0.0)
        if big > 24:
            warn('UV_LARGE', f'|uv| reaches {big:.1f} on {layer}: shorten chunks or enable full-precision UVs in UE')
    if uv_mode == 'UNIQUE':
        rows = m.uv['UV0_Main']
        if any(not (-1e-6 <= c <= 1 + 1e-6) for row in rows for uv in row for c in uv):
            err('UV_RANGE', 'UV0 leaves the 0–1 tile')
        boxes: dict[int, list[float]] = {}
        for f, row in enumerate(rows):
            b = boxes.setdefault(m.face_island[f], [1e9, 1e9, -1e9, -1e9])
            for u, v in row:
                b[0], b[1], b[2], b[3] = min(b[0], u), min(b[1], v), max(b[2], u), max(b[3], v)
        items = sorted(boxes.items())
        for i, (ia, a) in enumerate(items):
            for ib, b in items[i + 1:]:
                if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                    err('UV_OVERLAP', f'UV0 islands {ia} and {ib} overlap')
    return issues


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == 'ERROR']
