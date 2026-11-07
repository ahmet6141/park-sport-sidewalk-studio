"""One FBX per piece for UE5 and Substance Painter, plus an RD01_manifest.json (spec §7).

FBX settings follow spec D1–D5 (verified in Blender 4.5): Z up / Y forward with baked space
transform, unit scale 1 (centimetre vertices in the file), EDGE smoothing groups, MikkTSpace
tangents, sRGB byte colours, no exporter triangulation. Quads are triangulated by a temporary
modifier with the FIXED split (v0–v2), so Painter and UE see the same triangles.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import bpy
from ..core.piece import Piece
from ..core.qmesh import UV_LAYERS, COLOR_ID, COLOR_MASK
from . import mesh_io

FBX_KW = dict(
    use_selection=True, object_types={'MESH', 'EMPTY'}, global_scale=1.0, apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_NONE', axis_forward='Y', axis_up='Z', bake_space_transform=True,
    use_space_transform=True, mesh_smooth_type='EDGE', use_tspace=True, use_triangles=False,
    use_mesh_modifiers=True, colors_type='SRGB', prioritize_active_color=True, add_leaf_bones=False,
    bake_anim=False, use_custom_props=False, path_mode='AUTO', embed_textures=False,
)
SCHEMA = 'rd01.kit/1.0'


def blender_to_ue(location, yaw_deg: float) -> dict:
    """Blender metres, +Y left → UE centimetres, +Y right (spec §1.3)."""
    x, y, z = location
    return {'location_cm': [round(100 * x, 3), round(-100 * y, 3), round(100 * z, 3)], 'yaw_deg': round(-yaw_deg, 6)}


def _export_object(piece: Piece, collection: bpy.types.Collection, profile: str) -> list[bpy.types.Object]:
    me = mesh_io.qmesh_to_bpy(piece.mesh, piece.name)
    if profile == 'PAINTER':
        me.color_attributes.active_color = me.color_attributes[COLOR_ID]   # Painter reads the first colour layer
    ob = bpy.data.objects.new(piece.name + ('_low' if profile == 'PAINTER' else ''), me)
    collection.objects.link(ob)
    tri = ob.modifiers.new('RD01_Triangulate', 'TRIANGULATE')
    tri.quad_method = 'FIXED'; tri.ngon_method = 'BEAUTY'; tri.min_vertices = 4; tri.keep_custom_normals = True
    objs = [ob]
    if profile == 'UE':
        for s in piece.sockets:
            emp = bpy.data.objects.new('SOCKET_' + s.tag, None)
            collection.objects.link(emp)
            emp.parent = ob
            emp.location = s.position
            emp.rotation_euler = (0.0, 0.0, math.radians(s.yaw_deg))
            emp.empty_display_size = 0.5
            objs.append(emp)
    return objs


def export_pieces(pieces: list[Piece], folder: str | Path, profile: str = 'UE') -> Path:
    """Write one FBX per piece and the manifest. profile: 'UE' (sockets) or 'PAINTER' (*_low, ID layer first)."""
    out = Path(bpy.path.abspath(str(folder))).resolve()
    (out / 'Meshes').mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    collection = bpy.data.collections.new('RD01_EXPORT_TMP')
    scene.collection.children.link(collection)          # an excluded collection writes identity socket transforms
    records = []
    try:
        for piece in pieces:
            objs = _export_object(piece, collection, profile)
            bpy.context.view_layer.update()
            for o in bpy.context.view_layer.objects:
                o.select_set(False)
            for o in objs:
                o.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]
            path = out / 'Meshes' / f'{piece.name}.fbx'
            result = bpy.ops.export_scene.fbx(filepath=str(path), **FBX_KW)
            if 'FINISHED' not in result or not path.is_file():
                raise RuntimeError(f'FBX export failed for {piece.name}')
            me = objs[0].data
            records.append({
                'name': piece.name, 'file': f'Meshes/{piece.name}.fbx', 'slots': list(piece.mesh.slots),
                'uv_layers': list(UV_LAYERS), 'colors': [COLOR_MASK, COLOR_ID], 'tris': piece.mesh.tri_count(),
                'placement': blender_to_ue(piece.origin, piece.yaw_deg),
                'sockets': [{'tag': s.tag, **blender_to_ue(s.position, s.yaw_deg)} for s in piece.sockets],
                'meta': {k: v for k, v in piece.meta.items() if isinstance(v, (str, int, float, list, tuple))},
                'nanite': True, 'collision': 'complex_as_simple', 'full_precision_uvs': True,
            })
            for o in objs:
                bpy.data.objects.remove(o, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)
    finally:
        for o in list(collection.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(collection)
    manifest = {'schema': SCHEMA, 'units': 'cm', 'basis': 'ue_lh', 'profile': profile,
                'fbx': {k: (sorted(v) if isinstance(v, set) else v) for k, v in FBX_KW.items()}, 'assets': records}
    (out / 'RD01_manifest.json').write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    return out
