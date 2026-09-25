"""Blender scene transactions; never deletes unowned/SW01 objects.
No import-time scene mutations. Uses a staging collection before replacing a park.
"""
import bpy,math,json,uuid,traceback
from mathutils import Vector,Matrix
from .geometry import MATERIAL_NAMES
from . import materials


def safe_name(name):
    import re
    return re.sub(r'[^A-Za-z0-9_]+','_',name).strip('_')[:48] or 'PK01_Park'

def mesh_data(mesh,mats):
    import hashlib
    digest=hashlib.sha256((mesh.geometry_hash()+'|'.join(m.name for m in mats)).encode()).hexdigest();key=mesh.name+'__'+digest[:10]
    me=bpy.data.meshes.get(key)
    if me and me.get('pk01_hash')==digest:return me
    me=bpy.data.meshes.new(key)
    try:
        me.from_pydata(mesh.vertices,[],mesh.triangles);me.update(calc_edges=True)
        used=sorted(set(mesh.material_ids));remap={v:i for i,v in enumerate(used)}
        for i in used:me.materials.append(mats[i])
        me.polygons.foreach_set('material_index',[remap[i] for i in mesh.material_ids])
        me.polygons.foreach_set('use_smooth',mesh.smooth)
        uv=me.uv_layers.new(name='UV0_Tile');uv.data.foreach_set('uv',[v for t in mesh.uv for p in t for v in p])
        colors=me.color_attributes.new(name='SW01_Tint',type='FLOAT_COLOR',domain='POINT')
        colors.data.foreach_set('color',[min(1,max(0,v)) for c in mesh.colors for v in (*c,1)])
        me.color_attributes.active_color_index=0
        me['pk01_hash']=digest;me['pk01_slot_keys']=json.dumps([MATERIAL_NAMES[i] for i in used]);me.update()
        return me
    except Exception:
        if me.users==0:bpy.data.meshes.remove(me)
        raise

def all_collections(c):
    yield c
    for child in c.children:yield from all_collections(child)

def remove_owned(c,owner):
    """Detach user children with world transforms preserved; delete our objects only."""
    own=[o for o in c.all_objects if o.get('pk01_owner')==owner]
    ids={o.as_pointer() for o in own}
    for o in list(c.all_objects):
        if o.as_pointer() not in ids and o.parent and o.parent.as_pointer() in ids:
            world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
    for o in own:
        data=o.data if o.type=='MESH' else None
        bpy.data.objects.remove(o,do_unlink=True)
        if data and data.users==0:bpy.data.meshes.remove(data)
    for child in reversed(list(all_collections(c))):
        if len(child.objects)==0 and len(child.children)==0:bpy.data.collections.remove(child)

def find_collection(scene,key):
    for c in scene.collection.children:
        if c.get('pk01_project')==key:return c
    return None

def instantiate(plan,context,origin=(0,0,0),yaw=0,replace_existing=True,external_sw01='',external_native='',wetness=0.):
    if abs(context.scene.unit_settings.scale_length-1)>1e-6:
        raise ValueError('PK01 requires scene Unit Scale = 1.0 (metres). Use a new scene or set Scene Properties > Units > Unit Scale to 1.0 first.')
    if context.object and context.object.mode!='OBJECT':raise ValueError('Switch to Object Mode before building PK01.')
    key=safe_name(plan.name);old=find_collection(context.scene,key)
    if old and not replace_existing:raise ValueError('A park with this project name already exists. Choose a new name or Rebuild.')
    owner=uuid.uuid4().hex
    c=bpy.data.collections.new('PK01_STAGE_'+owner[:8]);c['pk01_owner']=owner;c['pk01_project']=key;context.scene.collection.children.link(c)
    created=[]
    try:
        mats=materials.ensure_materials(plan.settings.get('palette','COASTAL'),wetness,external_sw01,external_native)
        data={k:mesh_data(mesh,mats) for k,mesh in plan.assets.items()}
        root=bpy.data.objects.new('PK01_ROOT_'+key,None);c.objects.link(root);root['pk01_owner']=owner;root['pk01_root']=True
        root.location=origin;root.rotation_euler[2]=math.radians(yaw);root.empty_display_type='PLAIN_AXES';root.empty_display_size=3
        root['pk01_settings']=json.dumps(plan.settings);root['pk01_notes']=json.dumps(plan.notes);root['pk01_stats']=json.dumps(plan.stats())
        zones={};categories={}
        def cat(name):
            if name not in categories:
                coll=bpy.data.collections.new('PK01_'+key+'_'+name);c.children.link(coll);categories[name]=coll
            return categories[name]
        for z in plan.zones.values():
            o=bpy.data.objects.new('PK01_ZONE_'+z.name,None);cat(z.category).objects.link(o);o.parent=root;o.location=z.location;o.rotation_euler[2]=math.radians(z.yaw)
            o.empty_display_type='PLAIN_AXES';o.empty_display_size=1.;o['pk01_owner']=owner;o['pk01_zone']=True;o['pk01_settings']=json.dumps(z.settings);zones[z.name]=o
        for i,p in enumerate(plan.placements):
            mesh=plan.assets[p.asset];o=bpy.data.objects.new(p.asset+f'_{i:04d}',data[p.asset]);cat(p.category).objects.link(o)
            o.parent=zones.get(p.zone,root);o.location=p.location;o.rotation_euler[2]=math.radians(p.yaw);o.scale=p.scale
            o['pk01_owner']=owner;o['pk01_generated']=True;o['pk01_asset_key']=p.asset;o['pk01_category']=p.category
            o['pk01_collision']=json.dumps(mesh.collision);o['pk01_meta']=json.dumps(mesh.meta)
            if 'sw01' in mesh.meta:o['sw01_meta']=json.dumps(mesh.meta['sw01']);o['sw01_source_name']=p.asset
        for port in plan.ports:
            o=bpy.data.objects.new('SOCKET_'+port.name,None);cat('Connections').objects.link(o)
            o.parent=zones.get(port.zone,root);o.location=port.location;o.rotation_euler[2]=math.radians(port.yaw)
            o.empty_display_type='ARROWS';o.empty_display_size=.7;o.show_in_front=True;o.hide_render=True
            o['pk01_owner']=owner;o['pk01_port']=True;o['pk01_width']=port.width;o['pk01_height']=port.surface_height
            o['pk01_role']='ENTRY' if port.name.endswith('ENTRY') else ('OUT' if port.name.endswith('OUT') else 'IN')
        # Commit happens only after all geometry, materials and ports exist.
        if old:remove_owned(old,old.get('pk01_owner',''))
        c.name='PK01_'+key
        bpy.ops.object.select_all(action='DESELECT');root.select_set(True);context.view_layer.objects.active=root
        context.view_layer.update()
        for area in context.screen.areas if context.screen else ():
            if area.type=='VIEW_3D':area.spaces.active.clip_end=max(area.spaces.active.clip_end,3000.)
        return root,c
    except Exception:
        remove_owned(c,owner)
        raise

def root_from_object(obj):
    while obj:
        if obj.get('pk01_root'):return obj
        obj=obj.parent
    return None

def collection_from_root(root):
    if root:
        for c in root.users_collection:
            if c.get('pk01_project'):return c
    return None

def create_preview(context,root):
    collection=collection_from_root(root)
    if not collection:raise ValueError('Select a PK01 root or one of its generated objects.')
    # Reuse only PK01 preview objects, never user cameras/worlds.
    c=bpy.data.collections.new('PK01_Preview');collection.children.link(c);owner=root['pk01_owner']
    bounds=[]
    for o in collection.all_objects:
        if o.type=='MESH':bounds.extend(o.matrix_world@Vector(p) for p in o.bound_box)
    if not bounds:raise ValueError('No park mesh to frame.')
    center=sum(bounds,Vector())/len(bounds);extent=max((p-center).length for p in bounds)
    cam_data=bpy.data.cameras.new('PK01_Camera');cam=bpy.data.objects.new('PK01_Camera',cam_data);c.objects.link(cam)
    cam['pk01_owner']=owner;cam.location=center+Vector((1.1,-1.35,1.40))*extent
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam_data.type='ORTHO';cam_data.ortho_scale=extent*2.35
    context.scene.camera=cam
    light_data=bpy.data.lights.new('PK01_Sun','SUN');light_data.energy=2.2;light_data.angle=math.radians(6)
    sun=bpy.data.objects.new('PK01_Sun',light_data);c.objects.link(sun);sun['pk01_owner']=owner;sun.rotation_euler=(.42,-.57,-.45)
    world=bpy.data.worlds.new('PK01_Preview_World');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.58,.70,.85,1);world.node_tree.nodes['Background'].inputs[1].default_value=.35
    context.scene.world=world
    context.scene.render.engine='CYCLES';context.scene.cycles.samples=48;context.scene.cycles.use_denoising=True
    context.scene.render.resolution_x=1920;context.scene.render.resolution_y=1280;context.scene.render.resolution_percentage=100
    return cam

def replace_tree_mesh(context,source,root):
    if source is None or source.type!='MESH':raise ValueError('Choose one mesh tree with materials; join parts first or use a merged source.')
    c=collection_from_root(root)
    if not c:raise ValueError('Select a PK01 park first.')
    trees=[o for o in c.all_objects if o.get('pk01_category')=='Trees']
    if source in trees:raise ValueError('Use a separate source tree outside the generated collection.')
    deps=context.evaluated_depsgraph_get();evaluated=source.evaluated_get(deps)
    data=bpy.data.meshes.new_from_object(evaluated,depsgraph=deps)
    # Bake source rotation/scale, but not its world location; bottom-centre anchor.
    mat=source.matrix_world.to_3x3()
    for v in data.vertices:v.co=mat@v.co
    xmin,xmax=min(v.co.x for v in data.vertices),max(v.co.x for v in data.vertices)
    ymin,ymax=min(v.co.y for v in data.vertices),max(v.co.y for v in data.vertices)
    zmin=min(v.co.z for v in data.vertices);zmax=max(v.co.z for v in data.vertices)
    if not .3<zmax-zmin<50:bpy.data.meshes.remove(data);raise ValueError('Source tree height is outside .3..50 m. Check units.')
    for v in data.vertices:v.co-=Vector(((xmin+xmax)/2,(ymin+ymax)/2,zmin))
    data.update();data['pk01_external_tree']=True
    for o in trees:
        o.data=data;o['pk01_asset_key']='SM_PK01_ExternalTree';o['pk01_meta']=json.dumps({'external_tree':True,'foliage':True})
        o['pk01_collision']='[]'
    return len(trees)
