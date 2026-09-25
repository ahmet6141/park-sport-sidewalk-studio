"""FBX asset library + instance manifest export. Uses a dedicated temporary collection.
Exports a unique revision directory; never overwrites the user's existing export tree.
"""
from pathlib import Path
import bpy,math,json,uuid,shutil,hashlib,datetime
from mathutils import Matrix
from . import runtime,materials
from .geometry import Mesh,MAT
from .vendor import sw01_core as sw
from .contracts import convert_matrix


def _row_matrix(m):return [[float(v) for v in row] for row in m]

def _raw_object(name,verts,faces,collection):
    me=bpy.data.meshes.new(name+'_Data');me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);collection.objects.link(o);return o

def _box_object(name,bounds,c):
    x0,y0,z0,x1,y1,z1=bounds
    v=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    f=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return _raw_object(name,v,f,c)

def _export_one(src,name,out,c,meta):
    deps=bpy.context.evaluated_depsgraph_get();evaluated=src.evaluated_get(deps)
    data=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
    ob=bpy.data.objects.new(name,data);c.objects.link(ob);objects=[ob]
    try:
        for i,bounds in enumerate(meta.get('collision',[])):
            objects.append(_box_object(f'UCX_{name}_{i:03d}',bounds,c))
        swmeta=meta.get('sw01')
        if swmeta:
            path=sw.Path(swmeta['path']);dz=swmeta['config'].get('end_elevation',0.)
            for i,hull in enumerate(swmeta.get('collision',[])):
                m=sw.MeshData(f'UCX_{name}_{i:03d}')
                elev=(lambda p: dz*path.projection(p)/path.length) if dz else None
                m.prism(hull['polygon'],hull['z0'],hull['z1'],0,elevation=elev)
                objects.append(_raw_object(m.name,m.vertices,m.triangles,c))
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=ob
        result=bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'MESH'},
            axis_forward='-Y',axis_up='Z',global_scale=1.,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
            use_space_transform=True,bake_space_transform=False,use_mesh_modifiers=True,
            mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
        if 'FINISHED' not in result:raise RuntimeError('Blender FBX exporter did not finish: '+name)
        if not out.is_file() or out.stat().st_size<100:raise RuntimeError('FBX output is missing: '+str(out))
        return None
    finally:
        for o in objects:
            d=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if d and d.users==0:bpy.data.meshes.remove(d)

def _mat_description(mat,export_root):
    key=mat.get('pk01_surface_key',mat.name);result={'name':mat.name,'key':key,'textures':{}}
    if mat.get('pk01_spec'):
        result.update(json.loads(mat['pk01_spec']))
        paths=json.loads(mat.get('pk01_texture_paths','{}'))
    else:
        from .surfaces import SURFACES
        if key in SURFACES:
            result.update(SURFACES[key]);paths={}
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type=='TEX_IMAGE' and node.image:
                        p=Path(bpy.path.abspath(node.image.filepath))
                        for suffix in ('BaseColor','ORM','NormalGL'):
                            if suffix.lower() in p.name.lower():paths[suffix]=str(p)
            # SW01 images are reused by name, with the bundled package as a safe fallback.
            for suffix in ('BaseColor','ORM','NormalGL'):
                paths.setdefault(suffix,str(materials.texture_path(result['texture'],suffix)))
        else:
            result['external_material']=True;result['color']=list(mat.diffuse_color[:3]);result['roughness']=.7;result['metallic']=0.;paths={}
    for suffix,source in paths.items():
        p=Path(source)
        if not p.is_file():raise FileNotFoundError('Referenced texture no longer exists: '+str(p))
        tag=runtime.safe_name(result.get('texture') or key)
        dest=export_root/'Textures'/tag/f'{tag}_{suffix}.png';dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest);result['textures'][suffix]=str(dest.relative_to(export_root)).replace('\\','/')
        if suffix=='NormalGL':
            # Included normal maps have matching DX maps. User overrides may supply GL only;
            # importer then sets Flip Green Channel instead of fabricating a DX file.
            dx=p.with_name(p.name.replace('NormalGL','NormalDX'))
            if dx.is_file():
                out=dest.with_name(dest.name.replace('NormalGL','NormalDX'));shutil.copy2(dx,out)
                result['textures']['NormalDX']=str(out.relative_to(export_root)).replace('\\','/')
    return result

def export_park(context,root,directory,include_selected_sw01=False):
    c=runtime.collection_from_root(root)
    if not c:raise ValueError('Select a generated PK01 park root or one of its child objects.')
    if context.object and context.object.mode!='OBJECT':raise ValueError('Use Object Mode for export.')
    if not directory.strip():raise ValueError('Choose an export directory.')
    if directory.startswith('//') and not bpy.data.filepath:raise ValueError('Save the .blend or choose an absolute export directory first.')
    base=Path(bpy.path.abspath(directory)).expanduser().resolve();base.mkdir(parents=True,exist_ok=True)
    revision=runtime.safe_name(root.name.removeprefix('PK01_ROOT_'))+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:4]
    out=base/revision;out.mkdir();(out/'Meshes').mkdir()
    owner=root['pk01_owner'];objects=[o for o in c.all_objects if o.type=='MESH' and o.get('pk01_owner')==owner]
    selected=list(context.selected_objects);active=context.view_layer.objects.active
    if include_selected_sw01:
        for o in selected:
            if o.type=='MESH' and o.get('sw01_meta') and o not in objects and not o.name.startswith('UCX_'):objects.append(o)
    if not objects:raise ValueError('No exportable park meshes.')
    temp=bpy.data.collections.new('PK01_EXPORT_TEMP');context.scene.collection.children.link(temp)
    data={'schema':'pk01.scene/1.0','units':'metres','source_axes':'X forward / Y left / Z up','blender_version':bpy.app.version_string,
          'project':revision,'asset_map':{},'instances':[],'materials':{},'ports':[],'source':'PK01_1.0.0','ue_runtime_tested':False,
          'settings':json.loads(root.get('pk01_settings','{}')),'notes':json.loads(root.get('pk01_notes','[]'))}
    sources={};cache={}
    try:
        for o in objects:
            matrix=_row_matrix(o.matrix_world)
            convert_matrix(matrix,[[1,0,0],[0,1,0],[0,0,1]]) # reject sheared/mirrored transforms before writing any placement.
            matnames=tuple(slot.material.name if slot.material else '' for slot in o.material_slots)
            # Evaluated modifiers are unique unless the original datablock is unchanged and modifier-free.
            identity=(o.data.as_pointer(),matnames) if not o.modifiers else (o.as_pointer(),matnames)
            if identity not in cache:
                stem=runtime.safe_name(o.get('pk01_asset_key',o.get('sw01_source_name',o.name)))[:40]
                key=stem+'_'+hashlib.sha1((str(identity)).encode()).hexdigest()[:8]
                # Hash names are session-specific but preserved consistently throughout this export.
                info={'source_name':o.name,'file':'Meshes/'+key+'.fbx','materials':list(matnames),'collision':json.loads(o.get('pk01_collision','[]')),
                      'category':o.get('pk01_category','Paths'),'meta':json.loads(o.get('pk01_meta','{}'))}
                if o.get('sw01_meta'):info['sw01']=json.loads(o['sw01_meta'])
                data['asset_map'][key]=info;sources[key]=o;cache[identity]=key
                for slot in o.material_slots:
                    if slot.material and slot.material.name not in data['materials']:
                        data['materials'][slot.material.name]=_mat_description(slot.material,out)
            key=cache[identity]
            data['instances'].append({'asset':key,'label':o.name,'category':o.get('pk01_category','Paths'),'matrix_world_m':matrix})
        # Two off-centre, asymmetrical reference boxes detect units, XY signs and pivot shifts.
        for key,bounds in [('SM_PK01_CalX',(0,-.1,0,2,.1,.4)),('SM_PK01_CalY',(-.1,0,0,.1,3,.6))]:
            o=_box_object(key,bounds,temp);sources[key]=o;data['asset_map'][key]={'file':'Meshes/'+key+'.fbx','materials':[],'collision':[],'meta':{},'calibration':True}
        context.window_manager.progress_begin(0,len(sources))
        for i,(key,src) in enumerate(sources.items()):
            _export_one(src,key,out/data['asset_map'][key]['file'],temp,data['asset_map'][key]);context.window_manager.progress_update(i+1)
        for o in c.all_objects:
            if o.get('pk01_port'):
                data['ports'].append({'name':o.name,'matrix_world_m':_row_matrix(o.matrix_world),'width_m':o['pk01_width'],'surface_height_m':o['pk01_height'],'role':o.get('pk01_role','')})
        shutil.copy2(Path(__file__).parent/'unreal'/'PK01_Import.py',out/'PK01_Import.py')
        shutil.copy2(Path(__file__).parent/'contracts.py',out/'pk01_contracts.py')
        (out/'PK01_scene.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
        (out/'START_HERE.txt').write_text('PK01 Unreal bridge\nEnable Python Editor Script Plugin and Editor Scripting Utilities.\nRun PK01_Import.py in a blank test level.\nThe importer validates units/pivots before placing anything and NEVER saves the level.\nUE5.8 editor execution was not validated in the development environment.\n',encoding='utf-8')
        return out
    except Exception:
        (out/'EXPORT_FAILED.txt').write_text('Export failed. Incomplete folder kept for diagnosis; do not import it.\n',encoding='utf-8')
        raise
    finally:
        context.window_manager.progress_end()
        for o in list(temp.objects):
            d=o.data;bpy.data.objects.remove(o,do_unlink=True)
            if d and d.users==0:bpy.data.meshes.remove(d)
        bpy.data.collections.remove(temp)
        bpy.ops.object.select_all(action='DESELECT')
        for o in selected:
            if o.name in context.view_layer.objects:o.select_set(True)
        if active and active.name in context.view_layer.objects:context.view_layer.objects.active=active
