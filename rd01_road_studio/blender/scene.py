"""Generated-object ownership: RD01 only ever deletes objects it created for the same owner
(a curve or a kit root), identified by an ID property, never by name."""
from __future__ import annotations
import math
import uuid
import bpy
from mathutils import Matrix
from ..core.piece import Piece
from ..core.rail import Rail
from . import mesh_io

OWNER_KEY = 'rd01_owner'


def owner_key(owner: bpy.types.Object) -> str:
    if not owner.get('rd01_uid'):
        owner['rd01_uid'] = uuid.uuid4().hex[:12]
    return owner['rd01_uid']


def remove_generated(owner: bpy.types.Object) -> int:
    key = owner.get('rd01_uid')
    if not key:
        return 0
    doomed = [o for o in bpy.data.objects if o.get(OWNER_KEY) == key]
    meshes = {o.data for o in doomed if o.type == 'MESH'}
    for o in doomed:
        bpy.data.objects.remove(o, do_unlink=True)
    for me in meshes:
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return len(doomed)


def output_collection(context, name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        context.scene.collection.children.link(coll)
    return coll


def link_pieces(context, owner: bpy.types.Object, pieces: list[Piece], coll: bpy.types.Collection,
                parent_matrix: Matrix) -> list[bpy.types.Object]:
    key = owner_key(owner)
    out = []
    for p in pieces:
        me = mesh_io.qmesh_to_bpy(p.mesh, p.name)
        ob = bpy.data.objects.new(p.name, me)
        coll.objects.link(ob)
        ob.matrix_world = parent_matrix @ Matrix.Translation(p.origin)
        ob[OWNER_KEY] = key
        ob['rd01_piece'] = p.name
        for sk in p.sockets:
            emp = bpy.data.objects.new(f'SOCKET_{sk.tag}', None)
            coll.objects.link(emp)
            emp.parent = ob
            emp.location = sk.position
            emp.rotation_euler = (0.0, 0.0, math.radians(sk.yaw_deg))
            emp.empty_display_type = 'SINGLE_ARROW'
            emp.empty_display_size = 1.0
            emp[OWNER_KEY] = key
        out.append(ob)
    return out


def curve_rails(curve: bpy.types.Object) -> list[tuple[Rail, bool]]:
    """Rails (in the curve's local space) for every spline of a curve object, with a cyclic flag."""
    if curve.type != 'CURVE':
        raise ValueError('Select a curve object to build a road from.')
    sc = curve.matrix_world.to_scale()
    if any(abs(c - 1.0) > 1e-4 for c in sc):
        raise ValueError('Apply the curve object scale (Ctrl+A → Scale) before building a road.')
    rails = []
    for sp in curve.data.splines:
        if sp.type == 'BEZIER':
            pts = list(sp.bezier_points)
            pairs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if sp.use_cyclic_u else [])
            segs = [(tuple(a.co), tuple(a.handle_right), tuple(b.handle_left), tuple(b.co)) for a, b in pairs]
            if segs:
                rails.append((Rail.from_bezier(segs), sp.use_cyclic_u))
        else:
            pts = [tuple(p.co[:3]) for p in sp.points]
            if sp.use_cyclic_u:
                pts.append(pts[0])
            if len(pts) >= 2:
                rails.append((Rail(pts), sp.use_cyclic_u))
    if not rails:
        raise ValueError('The curve has no usable splines.')
    return rails
