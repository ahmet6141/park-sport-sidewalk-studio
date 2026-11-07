"""Blender mesh → QMesh (the inverse of mesh_io), so selected objects can be validated and exported
after the user has moved or lightly edited them."""
from __future__ import annotations
import bpy
from ..core.qmesh import QMesh, Kind, UV_LAYERS, COLOR_ID, COLOR_MASK, edge_key


def bpy_to_qmesh(ob: bpy.types.Object) -> QMesh:
    me = ob.data
    q = QMesh(ob.get('rd01_piece', ob.name))
    q.verts = [tuple(v.co) for v in me.vertices]
    q.faces = [tuple(p.vertices) for p in me.polygons]
    q.slots = [m.name if m else 'RD01_Unassigned' for m in me.materials] or ['RD01_Unassigned']
    q.face_slot = [p.material_index for p in me.polygons]
    q.face_part = [0] * len(q.faces)
    # Face kind: upward faces are treated as TOP (the height-field check needs it); others as SIDE.
    q.face_kind = [int(Kind.TOP) if p.normal.z >= 0.045 else int(Kind.SIDE) for p in me.polygons]
    q.face_island = [-1] * len(q.faces)
    for layer in UV_LAYERS:
        uv = me.uv_layers.get(layer)
        if uv is not None:
            q.uv[layer] = [tuple(tuple(uv.data[li].uv) for li in p.loop_indices) for p in me.polygons]
    for layer in (COLOR_ID, COLOR_MASK):
        attr = me.color_attributes.get(layer)
        if attr is not None and attr.domain == 'CORNER':
            q.colors[layer] = [tuple(tuple(round(c * 255) for c in attr.data[li].color_srgb) for li in p.loop_indices)
                               for p in me.polygons]
    sharp = me.attributes.get('sharp_edge')
    for e in me.edges:
        key = edge_key(*e.vertices)
        if sharp is not None and sharp.data[e.index].value:
            q.sharp.add(key)
        if e.use_seam:
            q.seams.add(key)
    return q
