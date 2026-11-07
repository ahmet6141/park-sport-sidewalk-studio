"""Modular kit catalogue (spec §6.1): straight and curved pieces on a metric grid.

Every piece runs along +X from its origin on the centreline at s = 0, with equal station
spacing (UE spline-mesh deformation), open port ends and Start/End sockets pointing outward.
Straight lengths are whole metres, so world/path UVs stay in phase from piece to piece.
"""
from __future__ import annotations
from dataclasses import dataclass
from .piece import Piece
from .rail import Rail
from .section import compile_section
from .standards import preset
from .sweep import RoadOptions, build_road


@dataclass(frozen=True)
class PieceDef:
    name: str
    kind: str              # 'STRAIGHT' | 'ARC'
    length: float = 0.0    # STRAIGHT (m)
    radius: float = 0.0    # ARC centre-line radius (m)
    angle: float = 0.0     # ARC degrees, + = left


def catalogue(section_preset: str = 'URBAN_2L') -> list[PieceDef]:
    family = section_preset.title().replace('_', '')
    out = [PieceDef(f'SM_RD01_{family}_L{round(L * 100):04d}', 'STRAIGHT', L) for L in (1.0, 2.0, 4.0, 8.0, 16.0)]
    for radius, angle in ((25.0, 22.5), (25.0, 45.0), (50.0, 22.5), (100.0, 11.25)):
        for sign, hand in ((1, 'L'), (-1, 'R')):
            out.append(PieceDef(f'SM_RD01_{family}_R{round(radius * 100):05d}_A{round(angle * 100):04d}{hand}',
                                'ARC', radius=radius, angle=sign * angle))
    return out


def build_piece(defn: PieceDef, section_preset: str = 'URBAN_2L', region: str = 'EU', markings: bool = True) -> Piece:
    tpl = compile_section(preset(section_preset, region))
    rail = Rail.line(defn.length) if defn.kind == 'STRAIGHT' else Rail.arc(defn.radius, defn.angle)
    # Dashes use whole ~4 m cycles, so every piece starts and ends at a cycle boundary and
    # neighbours chain in phase; 1–2 m fillers carry no markings.
    filler = defn.kind == 'STRAIGHT' and defn.length < 4.0
    opts = RoadOptions(name=defn.name, uniform=True, chunk_length=0, port_start=True, port_end=True,
                       markings=markings and not filler, dash_period=4.0, max_step=0.5)
    piece = build_road(rail, tpl, opts)[0]
    piece.meta.update(kind=defn.kind, length=round(rail.length, 6), radius=defn.radius, angle=defn.angle,
                      spline_boundary_cm=[0.0, round(rail.length * 100, 3)])
    return piece
