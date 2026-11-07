"""Trim sheets and UV channel rules (spec §4).

UV0_Main: Painter / macro layout (copy of UV1 for tiling pieces, packed atlas for kit pieces).
UV1_Tile: world XY, path (run × profile) or trim-sheet bands for Substance Designer materials.
UV2_Lane: lane-aligned asphalt UV (u along travel, v 0→1 from the driver's right edge).
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from .qmesh import QMesh

PX_PER_M = 1024.0


@dataclass(frozen=True)
class TrimBand:
    y0_m: float          # from the TOP of the sheet (Designer/Photoshop convention)
    height_m: float


@dataclass(frozen=True)
class TrimSheet:
    name: str
    width_m: float
    height_m: float
    bands: dict

    def band_v(self, band: str, d: float) -> float:
        b: TrimBand = self.bands[band]
        if not -1e-6 <= d <= b.height_m + 1e-6:
            raise ValueError(f'TRIM_OVERFLOW: profile distance {d:.3f} m exceeds band {self.name}/{band} '
                             f'({b.height_m:.3f} m).')
        return 1.0 - (b.y0_m + d) / self.height_m


# 1024 px/m (pedestrian texel class) sheets, 16 px padding around each band.
PAD = 16 / PX_PER_M
TRIM_SHEETS = {
    'RD01_TrimCurb': TrimSheet('RD01_TrimCurb', 2.0, 1.0, {'CURB': TrimBand(PAD, 0.62)}),
    'RD01_TrimGutter': TrimSheet('RD01_TrimGutter', 2.0, 1.0, {'GUTTER': TrimBand(PAD, 0.95)}),
}


def signed_area(uvs) -> float:
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(uvs, uvs[1:] + uvs[:1]))


def rebase(mesh: QMesh, layer: str) -> None:
    """Shift UVs by whole tiles so values stay small (half-float safe in UE).

    Run-following UVs are grouped by island and by the direction u runs along the face's first
    edge, so opposite-running lanes or the two walls of a marking shift independently; world-XY
    faces (mesh.meta['world_faces']) shift per island only, so curves get no extra UV splits.
    Integer shifts keep tiling textures seamless; trim-sheet v is never moved (it addresses a band).
    """
    rows = mesh.uv[layer]
    world = mesh.meta.get('world_faces', set()) if layer != 'UV2_Lane' else set()
    groups: dict[tuple, list[int]] = {}
    for f, isl in enumerate(mesh.face_island):
        row = rows[f]
        du = row[1][0] - row[0][0]
        key = (isl, 'world') if f in world else (isl, du > 0, du < 0)
        groups.setdefault(key, []).append(f)
    for faces in groups.values():
        us = [uv[0] for f in faces for uv in rows[f]]; vs = [uv[1] for f in faces for uv in rows[f]]
        du = math.floor(min(us)); dv = math.floor(min(vs))
        if mesh.slots[mesh.face_slot[faces[0]]].startswith('RD01_Trim'):
            dv = 0
        for f in faces:
            rows[f] = tuple((u - du, v - dv) for u, v in rows[f])


def max_abs_uv(mesh: QMesh, layer: str) -> float:
    return max((abs(c) for row in mesh.uv.get(layer, []) for uv in row for c in uv), default=0.0)


def shelf_pack(rects: list[tuple[float, float]], padding: float) -> tuple[list[tuple[float, float]], float]:
    """Pack (w, h) rectangles without rotation, tallest first, into a square of minimal side.
    Returns the lower-left corners and the side length (same units as the input)."""
    if not rects:
        return [], 0.0
    order = sorted(range(len(rects)), key=lambda i: (-rects[i][1], -rects[i][0], i))
    area = sum((w + padding) * (h + padding) for w, h in rects)
    side = max(math.sqrt(area), max(w + padding for w, h in rects), max(h + padding for w, h in rects))
    for _ in range(200):
        pos = [None] * len(rects)
        x = y = shelf_h = 0.0
        ok = True
        for i in order:
            w, h = rects[i][0] + padding, rects[i][1] + padding
            if x + w > side + 1e-12:
                x, y, shelf_h = 0.0, y + shelf_h, 0.0
            if y + h > side + 1e-12:
                ok = False
                break
            pos[i] = (x + padding / 2, y + padding / 2)
            x += w; shelf_h = max(shelf_h, h)
        if ok:
            return pos, side
        side *= 1.03
    raise ValueError('UV packing did not converge.')
