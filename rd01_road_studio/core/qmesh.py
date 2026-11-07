"""Quad mesh buffer for RD01 (spec §1.4). Pure Python, no bpy.

Units: metres, Blender frame (right-handed, +Z up). Faces are quads wound CCW seen
from outside; triangles are only allowed where a vertex carries a 'pole:' tag.
Per-corner data (UV layers, colour attributes) is stored per face, so seams and
hard edges never need duplicated vertices.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
import hashlib
import json
import math

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
RGBA8 = tuple[int, int, int, int]
Edge = tuple[int, int]

UV_LAYERS = ('UV0_Main', 'UV1_Tile', 'UV2_Lane')
COLOR_ID, COLOR_MASK = 'RD01_ID', 'RD01_Mask'


class Part(IntEnum):
    """Surface zone → flat RD01_ID colour (Painter ID mask, spec §1.4)."""
    HIDDEN = 0; LANE = 1; SHOULDER = 2; GUTTER = 3; CURB_FACE = 4; CURB_ARRIS = 5; CURB_TOP = 6
    SIDEWALK = 7; RAMP = 8; TACTILE = 9; MARKING = 10; ISLAND_TOP = 11; APRON = 12; VERGE = 13
    GRAVEL = 14; DITCH = 15; BARRIER_FACE = 16; BARRIER_TOP = 17; RAIL = 18; POST = 19; CAP = 20
    MEDIAN_FLUSH = 21


ID_COLOURS: dict[Part, tuple[int, int, int]] = {
    Part.HIDDEN: (0, 0, 0), Part.LANE: (255, 0, 0), Part.SHOULDER: (255, 128, 0), Part.GUTTER: (255, 255, 0),
    Part.CURB_FACE: (0, 255, 0), Part.CURB_ARRIS: (0, 128, 255), Part.CURB_TOP: (0, 255, 255),
    Part.SIDEWALK: (0, 0, 255), Part.RAMP: (128, 0, 255), Part.TACTILE: (255, 0, 255), Part.MARKING: (255, 255, 255),
    Part.ISLAND_TOP: (0, 128, 0), Part.APRON: (128, 64, 0), Part.VERGE: (128, 255, 0), Part.GRAVEL: (192, 160, 96),
    Part.DITCH: (128, 0, 0), Part.BARRIER_FACE: (0, 0, 128), Part.BARRIER_TOP: (0, 128, 128), Part.RAIL: (192, 192, 192),
    Part.POST: (64, 64, 64), Part.CAP: (128, 128, 0), Part.MEDIAN_FLUSH: (255, 96, 96),
}


class Kind(IntEnum):
    """Face kind: TOP faces form the drivable/walkable height field (n_z ≥ 0.045)."""
    TOP = 0; SKIRT = 1; BOTTOM = 2; CAP = 3; SIDE = 4; MARKING = 5


def edge_key(a: int, b: int) -> Edge:
    return (a, b) if a < b else (b, a)


@dataclass
class QMesh:
    name: str
    verts: list[Vec3] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)
    slots: list[str] = field(default_factory=list)
    face_slot: list[int] = field(default_factory=list)
    face_part: list[int] = field(default_factory=list)
    face_kind: list[int] = field(default_factory=list)
    face_island: list[int] = field(default_factory=list)
    uv: dict[str, list[tuple[Vec2, ...]]] = field(default_factory=dict)
    colors: dict[str, list[tuple[RGBA8, ...]]] = field(default_factory=dict)
    sharp: set[Edge] = field(default_factory=set)
    seams: set[Edge] = field(default_factory=set)
    vtags: dict[int, str] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    # -------------------------------------------------------------- building
    def slot(self, name: str) -> int:
        if name not in self.slots:
            self.slots.append(name)
        return self.slots.index(name)

    def add_vert(self, p: Vec3) -> int:
        if not all(math.isfinite(c) for c in p):
            raise ValueError(f'{self.name}: non-finite vertex {p}')
        self.verts.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.verts) - 1

    def add_face(self, vids, slot: str, part: Part, kind: Kind = Kind.TOP, island: int = -1,
                 uvs: dict[str, tuple[Vec2, ...]] | None = None) -> int:
        vids = tuple(vids)
        if len(vids) not in (3, 4) or len(set(vids)) != len(vids):
            raise ValueError(f'{self.name}: face must be a quad (or pole triangle) with distinct ids: {vids}')
        self.faces.append(vids)
        self.face_slot.append(self.slot(slot))
        self.face_part.append(int(part))
        self.face_kind.append(int(kind))
        self.face_island.append(island)
        for layer, corners in (uvs or {}).items():
            self.uv.setdefault(layer, [None] * (len(self.faces) - 1)).append(tuple(corners))
        for layer, rows in self.uv.items():
            if len(rows) < len(self.faces):
                rows.append(None)
        return len(self.faces) - 1

    def mark_edge(self, a: int, b: int, sharp: bool = True, seam: bool = True) -> None:
        e = edge_key(a, b)
        if sharp:
            self.sharp.add(e)
        if seam:
            self.seams.add(e)

    def append(self, other: 'QMesh') -> dict[int, int]:
        """Append another mesh as a separate component; returns the vertex id map."""
        vmap = {i: self.add_vert(p) for i, p in enumerate(other.verts)}
        slot_map = {i: self.slot(s) for i, s in enumerate(other.slots)}
        base = len(self.faces)
        islands = max(self.face_island, default=-1) + 1
        for f, vids in enumerate(other.faces):
            self.faces.append(tuple(vmap[v] for v in vids))
            self.face_slot.append(slot_map[other.face_slot[f]])
            self.face_part.append(other.face_part[f])
            self.face_kind.append(other.face_kind[f])
            self.face_island.append(other.face_island[f] + islands if other.face_island[f] >= 0 else -1)
        for layer in set(self.uv) | set(other.uv):
            mine = self.uv.setdefault(layer, [None] * base)
            mine.extend(other.uv.get(layer, [None] * len(other.faces)))
        for layer in set(self.colors) | set(other.colors):
            mine = self.colors.setdefault(layer, [None] * base)
            mine.extend(other.colors.get(layer, [None] * len(other.faces)))
        self.sharp |= {edge_key(vmap[a], vmap[b]) for a, b in other.sharp}
        self.seams |= {edge_key(vmap[a], vmap[b]) for a, b in other.seams}
        for v, tag in other.vtags.items():
            self.vtags[vmap[v]] = tag
        return vmap

    def prune_slots(self) -> None:
        """Drop unused material slots, keeping the order of the remaining ones."""
        used = sorted(set(self.face_slot))
        remap = {old: new for new, old in enumerate(used)}
        self.slots = [self.slots[i] for i in used]
        self.face_slot = [remap[s] for s in self.face_slot]

    # -------------------------------------------------------------- queries
    def edge_faces(self) -> dict[Edge, list[int]]:
        out: dict[Edge, list[int]] = {}
        for f, vids in enumerate(self.faces):
            for a, b in zip(vids, vids[1:] + vids[:1]):
                out.setdefault(edge_key(a, b), []).append(f)
        return out

    def components(self) -> list[list[int]]:
        """Face-connected components (faces sharing a vertex)."""
        parent = list(range(len(self.verts)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for vids in self.faces:
            r = find(vids[0])
            for v in vids[1:]:
                parent[find(v)] = r
        groups: dict[int, list[int]] = {}
        for f, vids in enumerate(self.faces):
            groups.setdefault(find(vids[0]), []).append(f)
        return list(groups.values())

    def face_normal(self, f: int) -> Vec3:
        """Newell normal (unit) of face f."""
        pts = [self.verts[v] for v in self.faces[f]]
        nx = ny = nz = 0.0
        for (x0, y0, z0), (x1, y1, z1) in zip(pts, pts[1:] + pts[:1]):
            nx += (y0 - y1) * (z0 + z1); ny += (z0 - z1) * (x0 + x1); nz += (x0 - x1) * (y0 + y1)
        n = math.sqrt(nx * nx + ny * ny + nz * nz)
        return (0.0, 0.0, 0.0) if n < 1e-15 else (nx / n, ny / n, nz / n)

    def face_area(self, f: int) -> float:
        pts = [self.verts[v] for v in self.faces[f]]
        nx = ny = nz = 0.0
        for (x0, y0, z0), (x1, y1, z1) in zip(pts, pts[1:] + pts[:1]):
            nx += (y0 - y1) * (z0 + z1); ny += (z0 - z1) * (x0 + x1); nz += (x0 - x1) * (y0 + y1)
        return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)

    def tri_count(self) -> int:
        return sum(len(f) - 2 for f in self.faces)

    def bounds(self) -> tuple[Vec3, Vec3]:
        if not self.verts:
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
        return (tuple(min(p[i] for p in self.verts) for i in range(3)),
                tuple(max(p[i] for p in self.verts) for i in range(3)))

    def check_buffers(self) -> None:
        n = len(self.faces)
        for name, buf in (('face_slot', self.face_slot), ('face_part', self.face_part),
                          ('face_kind', self.face_kind), ('face_island', self.face_island)):
            if len(buf) != n:
                raise AssertionError(f'{self.name}: {name} has {len(buf)} entries for {n} faces')
        for layer, rows in list(self.uv.items()) + list(self.colors.items()):
            if len(rows) != n or any(r is None or len(r) != len(self.faces[i]) for i, r in enumerate(rows)):
                raise AssertionError(f'{self.name}: layer {layer} is incomplete')
        for vids in self.faces:
            if any(not 0 <= v < len(self.verts) for v in vids):
                raise AssertionError(f'{self.name}: face references a missing vertex')

    def geometry_hash(self) -> str:
        data = [[round(c, 6) for p in self.verts for c in p], self.faces, self.slots, self.face_slot,
                self.face_part, sorted(self.sharp), sorted(self.seams)]
        return hashlib.blake2b(json.dumps(data, separators=(',', ':')).encode(), digest_size=16).hexdigest()

    def uv_hash(self, layer: str = 'UV0_Main') -> str:
        data = [[round(c, 6) for corner in row for c in corner] for row in self.uv.get(layer, [])]
        return hashlib.blake2b(json.dumps(data).encode(), digest_size=16).hexdigest()
