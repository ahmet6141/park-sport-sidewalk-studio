"""QMesh → Blender mesh datablock (quads, slots, UV layers in contract order, colour attributes,
sharp edges and seams). Faces are smooth; hard edges come from the 'sharp_edge' attribute, so
Blender, the FBX smoothing groups (EDGE) and UE agree on the split normals."""
from __future__ import annotations
import bpy
from ..core.qmesh import QMesh, UV_LAYERS, COLOR_ID, COLOR_MASK

# Viewport-only base colours per texture set (the real look comes from Substance).
SLOT_COLOURS = {
    'RD01_Asphalt': (0.045, 0.047, 0.05), 'RD01_TrimCurb': (0.42, 0.41, 0.39), 'RD01_TrimGutter': (0.30, 0.30, 0.29),
    'RD01_Concrete': (0.50, 0.49, 0.46), 'RD01_Grass': (0.12, 0.22, 0.06), 'RD01_Gravel': (0.33, 0.29, 0.23),
    'RD01_Soil': (0.20, 0.14, 0.09), 'RD01_Marking': (0.85, 0.85, 0.82), 'RD01_TrimBarrier': (0.55, 0.55, 0.53),
    'RD01_Kit': (0.5, 0.5, 0.5),
}


def ensure_material(name: str) -> bpy.types.Material:
    """Return the RD01 material for a texture set, creating a simple viewport material if needed.
    Existing materials of that name are reused unchanged (they may carry the user's look-dev)."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*SLOT_COLOURS.get(name, (0.5, 0.5, 0.5)), 1.0)
        mat['rd01_material'] = True
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get('Principled BSDF')
        if bsdf:
            bsdf.inputs['Base Color'].default_value = mat.diffuse_color
            bsdf.inputs['Roughness'].default_value = 0.85
    return mat


def qmesh_to_bpy(q: QMesh, name: str | None = None) -> bpy.types.Mesh:
    q.check_buffers()
    me = bpy.data.meshes.new(name or q.name)
    me.from_pydata(q.verts, [], q.faces)
    me.update(calc_edges=True)
    for slot in q.slots:
        me.materials.append(ensure_material(slot))
    me.polygons.foreach_set('material_index', q.face_slot)
    me.polygons.foreach_set('use_smooth', [True] * len(q.faces))
    # Polygon order and loop order follow q.faces exactly (from_pydata keeps them).
    for layer in UV_LAYERS:
        uv = me.uv_layers.new(name=layer)
        uv.data.foreach_set('uv', [c for row in q.uv[layer] for corner in row for c in corner])
    for layer in (COLOR_MASK, COLOR_ID):
        attr = me.color_attributes.new(name=layer, type='BYTE_COLOR', domain='CORNER')
        values = [c / 255.0 for row in q.colors[layer] for corner in row for c in corner]
        attr.data.foreach_set('color_srgb', values)        # bytes arrive unchanged in the FBX (spec D3)
    me.color_attributes.active_color = me.color_attributes[COLOR_MASK]
    me.color_attributes.render_color_index = me.color_attributes.find(COLOR_MASK)
    edge_index = {tuple(sorted(e.vertices)): e.index for e in me.edges}
    sharp = [False] * len(me.edges)
    for a, b in q.sharp:
        sharp[edge_index[(a, b)]] = True
    attr = me.attributes.get('sharp_edge') or me.attributes.new('sharp_edge', 'BOOLEAN', 'EDGE')
    attr.data.foreach_set('value', sharp)
    seams = [False] * len(me.edges)
    for a, b in q.seams:
        seams[edge_index[(a, b)]] = True
    me.edges.foreach_set('use_seam', seams)
    me.validate(clean_customdata=False)
    me.update()
    return me
