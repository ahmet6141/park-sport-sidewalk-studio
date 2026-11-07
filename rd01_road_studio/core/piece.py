"""Piece records: a finished mesh plus its frame, sockets and metadata (spec §1.3, §7.5)."""
from __future__ import annotations
from dataclasses import dataclass, field
from .qmesh import QMesh, Vec3


@dataclass(frozen=True)
class Socket:
    """Snapping socket. +X of the socket points OUT of the piece (spec D10); yaw in degrees about +Z."""
    tag: str
    position: Vec3
    yaw_deg: float


@dataclass
class Piece:
    name: str
    mesh: QMesh
    origin: Vec3 = (0.0, 0.0, 0.0)          # placement of the piece frame in the source (curve object) space
    yaw_deg: float = 0.0
    sockets: list[Socket] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
