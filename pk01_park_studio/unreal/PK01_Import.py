"""PK01 UE5.8-targeted EDITOR bridge. Not a runtime game plugin.
Run the exported copy beside PK01_scene.json from Unreal's Execute Python Script.
Native UE execution was NOT available in the development environment.
"""
from pathlib import Path
import json,math,traceback,importlib.util,sys
import unreal

EXPORT_ROOT_OVERRIDE = r''
CONTENT_ROOT = '/Game/PK01'
REIMPORT_OWN_ASSETS = False
PLACE_SCENE = True
REPLACE_SAME_SCENE = False
WATER_MATERIAL_PATH = ''  # Optional existing Unreal material/MI. Never edited by PK01.
GLASS_MATERIAL_PATH = ''
REUSE_EXISTING_SW01_MATERIALS = True
SW01_CONTENT_ROOT = '/Game/SW01'  # Reuse existing MI_SW01_* without modifying them.

ROOT=Path(EXPORT_ROOT_OVERRIDE).expanduser().resolve() if EXPORT_ROOT_OVERRIDE else Path(__file__).resolve().parent
EAL=unreal.EditorAssetLibrary;MEL=unreal.MaterialEditingLibrary;TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
OWNER='PK01_ParkStudio_1';WARNINGS=[]

def log(x):unreal.log('[PK01] '+str(x))
def warn(x):WARNINGS.append(str(x));unreal.log_warning('[PK01] '+str(x))
def prop(o,k,v):
    try:o.set_editor_property(k,v)
    except Exception as e:raise RuntimeError(f'Unsupported editor property {k} on {o.get_class().get_name()}: {e}') from e

def owned(o):return EAL.get_metadata_tag(o,'PK01_Owner')==OWNER

def save(o):
    EAL.set_metadata_tag(o,'PK01_Owner',OWNER);EAL.save_loaded_asset(o,only_if_is_dirty=False)

def in_folder(folder,cls):
    if not EAL.does_directory_exist(folder):return []
    return [o for p in EAL.list_assets(folder,recursive=True,include_folder=False) if isinstance(o:=EAL.load_asset(p),cls)]

def import_one(source,folder,name,cls,options=None):
    if not source.is_file():raise FileNotFoundError(str(source))
    prev=in_folder(folder,cls)
    if prev:
        if len(prev)!=1 or not owned(prev[0]):raise RuntimeError('Refusing to replace an unowned/ambiguous asset in '+folder)
        if not REIMPORT_OWN_ASSETS:
            old=EAL.get_metadata_tag(prev[0],'PK01_Source')
            if old and Path(old)!=source:raise RuntimeError('Asset source changed. Use a new CONTENT_ROOT or explicitly enable REIMPORT_OWN_ASSETS.')
            return prev[0]
    task=unreal.AssetImportTask()
    for k,v in dict(filename=str(source),destination_path=folder,destination_name=name,automated=True,replace_existing=REIMPORT_OWN_ASSETS,save=True).items():prop(task,k,v)
    if options:prop(task,'options',options)
    try:task.set_editor_property('async_',False)
    except Exception:pass
    EAL.make_directory(folder);TOOLS.import_asset_tasks([task])
    try:result=[o for o in task.get_objects() if isinstance(o,cls)]
    except Exception:result=[]
    if not result:result=in_folder(folder,cls)
    if len(result)!=1:raise RuntimeError(f'{source.name}: expected 1 {cls.__name__}, got {len(result)}. Inspect Interchange / Output Log.')
    obj=result[0];EAL.set_metadata_tag(obj,'PK01_Source',str(source));save(obj);return obj

def get_asset(path,cls,factory):
    if EAL.does_asset_exist(path):
        o=EAL.load_asset(path)
        if not isinstance(o,cls) or not owned(o):raise RuntimeError('Unowned asset exists: '+path)
        return o,False
    folder,name=path.rsplit('/',1);EAL.make_directory(folder);o=TOOLS.create_asset(name,folder,cls,factory)
    if o is None:raise RuntimeError('Cannot create '+path)
    save(o);return o,True


def import_texture(rel,kind):
    name='T_'+Path(rel).stem;folder=f'{CONTENT_ROOT}/Textures/{name}'
    tex=import_one(ROOT/rel,folder,name,unreal.Texture2D)
    prop(tex,'srgb',kind=='BaseColor')
    compression={'BaseColor':unreal.TextureCompressionSettings.TC_DEFAULT,'ORM':unreal.TextureCompressionSettings.TC_MASKS,'NormalGL':unreal.TextureCompressionSettings.TC_NORMALMAP,'NormalDX':unreal.TextureCompressionSettings.TC_NORMALMAP}[kind]
    prop(tex,'compression_settings',compression)
    if kind.startswith('Normal'):prop(tex,'flip_green_channel',kind=='NormalGL')
    save(tex);return tex

def make_material(d):
    key=d.get('key',d['name']);override=WATER_MATERIAL_PATH if d.get('water') else (GLASS_MATERIAL_PATH if key.endswith('Glass') else '')
    if override:
        mat=EAL.load_asset(override)
        if not isinstance(mat,unreal.MaterialInterface):raise ValueError('Material override not found: '+override)
        return mat
    if d.get('sw01') and REUSE_EXISTING_SW01_MATERIALS:
        role=key.removeprefix('M_SW01_')
        path=f'{SW01_CONTENT_ROOT}/Materials/MI_SW01_{role}'
        if EAL.does_asset_exist(path):
            shared=EAL.load_asset(path)
            if isinstance(shared,unreal.MaterialInterface):
                log('Reusing existing SW01 material without edits: '+path);return shared
            raise ValueError('SW01 material path exists but is not a MaterialInterface: '+path)
    name=d['name'];path=f'{CONTENT_ROOT}/Materials/{name}_Master'
    mat,new=get_asset(path,unreal.Material,unreal.MaterialFactoryNew())
    if new or EAL.get_metadata_tag(mat,'PK01_Ready')!='1':
        MEL.delete_all_material_expressions(mat)
        def node(cls,x,y,**kw):
            n=MEL.create_material_expression(mat,cls,x,y)
            if n is None:raise RuntimeError('Cannot create material node '+cls.__name__)
            for k,v in kw.items():prop(n,k,v)
            return n
        def conn(a,ap,b,bp):
            if not MEL.connect_material_expressions(a,ap,b,bp):raise RuntimeError('Material pin connection failed: '+str(bp))
        def output(a,p,channel):
            if not MEL.connect_material_property(a,p,channel):raise RuntimeError('Material output failed: '+str(channel))
        def scalar(n,v,x,y):return node(unreal.MaterialExpressionScalarParameter,x,y,parameter_name=n,default_value=float(v))
        color=d.get('color',(1,1,1));tint=node(unreal.MaterialExpressionVectorParameter,-600,-300,parameter_name='Tint',default_value=unreal.LinearColor(*color,1))
        vc=node(unreal.MaterialExpressionVertexColor,-600,-500)
        mul=node(unreal.MaterialExpressionMultiply,-280,-250);conn(tint,'RGB',mul,'A');conn(vc,'RGB',mul,'B');base=mul
        tex=d.get('textures',{})
        for kind in ('BaseColor','ORM','NormalDX' if 'NormalDX' in tex else 'NormalGL'):
            if kind not in tex:continue
            t=import_texture(tex[kind],kind)
            sampler=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind.startswith('Normal') else (unreal.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
            n=node(unreal.MaterialExpressionTextureSampleParameter2D,-900,{'BaseColor':0,'ORM':400,'NormalDX':800,'NormalGL':800}[kind],parameter_name=kind,texture=t,sampler_type=sampler)
            if kind=='BaseColor':
                m=node(unreal.MaterialExpressionMultiply,0,-50);conn(base,'',m,'A');conn(n,'RGB',m,'B');base=m
            elif kind=='ORM':
                rough=scalar('RoughnessScale',d.get('roughness_scale',1.),-580,620);mult=node(unreal.MaterialExpressionMultiply,-160,440);conn(n,'G',mult,'A');conn(rough,'',mult,'B')
                output(mult,'',unreal.MaterialProperty.MP_ROUGHNESS);output(n,'R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
                if d.get('sw01'):output(n,'B',unreal.MaterialProperty.MP_METALLIC)
            else:output(n,'RGB',unreal.MaterialProperty.MP_NORMAL)
        output(base,'',unreal.MaterialProperty.MP_BASE_COLOR)
        if 'ORM' not in tex:output(scalar('Roughness',d.get('roughness',.7),0,450),'',unreal.MaterialProperty.MP_ROUGHNESS)
        if not(d.get('sw01') and 'ORM' in tex):output(scalar('Metallic',d.get('metallic',0),0,630),'',unreal.MaterialProperty.MP_METALLIC)
        if d.get('emission'):
            strength=scalar('EmissionStrength',d['emission'],0,-630);mul=node(unreal.MaterialExpressionMultiply,250,-500);conn(tint,'RGB',mul,'A');conn(strength,'',mul,'B');output(mul,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if d.get('transmission'):
            # A simple translucent preview, NOT a converted Blender transmission model or WaterBody.
            prop(mat,'blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
            output(scalar('Opacity',.80 if d.get('water') else .25,250,800),'',unreal.MaterialProperty.MP_OPACITY)
        prop(mat,'two_sided',bool(d.get('two_sided',False)))
        try:MEL.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        except Exception as e:warn('Instanced material flag: '+str(e))
        MEL.recompile_material(mat);EAL.set_metadata_tag(mat,'PK01_Ready','1');save(mat)
    mi,new=get_asset(f'{CONTENT_ROOT}/Materials/MI_{name.removeprefix("M_")}',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    if new:MEL.set_material_instance_parent(mi,mat);MEL.update_material_instance(mi);save(mi)
    if d.get('external_material'):warn('External custom tree material uses a colour fallback; assign your original UE material: '+name)
    return mi


def fbx_options():
    o=unreal.FbxImportUI()
    for k,v in dict(import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH).items():prop(o,k,v)
    d=o.get_editor_property('static_mesh_import_data')
    for k,v in dict(combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=True,import_uniform_scale=1.,vertex_color_import_option=unreal.VertexColorImportOption.REPLACE,normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS).items():prop(d,k,v)
    return o

def bounds(mesh):
    b=mesh.get_bounding_box();return ((b.min.x,b.min.y,b.min.z),(b.max.x,b.max.y,b.max.z))

def sockets(mesh,description,basis):
    from_types=description.get('sw01')
    if not from_types:return
    for tag in ('in','out'):
        key='SW01_'+tag.upper();s=mesh.find_socket(key)
        if s is None:s=unreal.StaticMeshSocket(outer=mesh);prop(s,'socket_name',key);mesh.add_socket(s)
        p=from_types[tag]['location'];a=math.radians(from_types[tag]['yaw_degrees']);d=[math.cos(a),math.sin(a),0]
        location=[100*sum(basis[i][j]*p[j] for j in range(3)) for i in range(3)];direction=[sum(basis[i][j]*d[j] for j in range(3)) for i in range(3)]
        prop(s,'relative_location',unreal.Vector(*location));prop(s,'relative_rotation',unreal.Rotator(pitch=0,yaw=math.degrees(math.atan2(direction[1],direction[0])),roll=0));prop(s,'relative_scale',unreal.Vector(1,1,1))
    save(mesh)

def main():
    if not CONTENT_ROOT.startswith('/Game/') or len(CONTENT_ROOT)<7:raise ValueError('Use a dedicated /Game/PK01 folder, not /Game itself.')
    if (ROOT/'EXPORT_FAILED.txt').exists():raise RuntimeError('This export was incomplete; export again in Blender.')
    source=ROOT/'PK01_scene.json'
    if not source.is_file():raise FileNotFoundError('Execute the EXPORTED script beside PK01_scene.json, not the add-on source copy.')
    data=json.loads(source.read_text(encoding='utf-8'))
    if data.get('schema')!='pk01.scene/1.0':raise ValueError('Unsupported scene manifest schema.')
    spec=importlib.util.spec_from_file_location('_pk01_contracts',ROOT/'pk01_contracts.py');contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    opts=fbx_options();meshes={}
    for key in ('SM_PK01_CalX','SM_PK01_CalY'):
        d=data['asset_map'][key];meshes[key]=import_one(ROOT/d['file'],f'{CONTENT_ROOT}/Meshes/{key}',key,unreal.StaticMesh,opts)
    basis=contract.infer_basis(bounds(meshes['SM_PK01_CalX']),bounds(meshes['SM_PK01_CalY']));log('Measured import basis: '+str(basis))
    # Validate the complete instance list BEFORE touching the current level.
    transforms=[contract.convert_matrix(d['matrix_world_m'],basis) for d in data['instances']]
    mats={name:make_material(d) for name,d in data['materials'].items()}
    for key,d in data['asset_map'].items():
        if key in meshes:continue
        mesh=import_one(ROOT/d['file'],f'{CONTENT_ROOT}/Meshes/{key}',key,unreal.StaticMesh,opts);meshes[key]=mesh
        slots=mesh.get_editor_property('static_materials')
        for i,slot in enumerate(slots):
            candidates=[str(slot.get_editor_property('material_slot_name'))]
            try:candidates.append(str(slot.get_editor_property('imported_material_slot_name')))
            except Exception:pass
            match=next((name for name in d.get('materials',[]) if any(name==s or name in s for s in candidates)),None)
            if match in mats:mesh.set_material(i,mats[match])
            elif d.get('materials'):warn(f'{key}: unmatched slot {i}: {candidates}; assign a MI manually.')
        meta=d.get('meta',{})
        if meta.get('complex_collision') or meta.get('collision_note'):
            body=mesh.get_editor_property('body_setup')
            if body:prop(body,'collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            else:warn('BodySetup missing for static terrain/track collision: '+key)
        sockets(mesh,d,basis);save(mesh)
    api=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);spawned=[]
    scene_tag='PK01_SCENE_'+data['project']
    previous=[a for a in api.get_all_level_actors() if a.actor_has_tag(scene_tag)]
    if previous and not REPLACE_SAME_SCENE:raise RuntimeError('This scene already exists. It was preserved. Change revision or explicitly set REPLACE_SAME_SCENE.')
    if PLACE_SCENE:
        try:
            with unreal.ScopedEditorTransaction('PK01 place park scene'):
                for d,(location,quat,scale) in zip(data['instances'],transforms):
                    rotation=unreal.Quat(*quat).rotator();actor=api.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(*location),rotation)
                    if actor is None:raise RuntimeError('Cannot spawn static mesh actor.')
                    spawned.append(actor);actor.static_mesh_component.set_static_mesh(meshes[d['asset']]);actor.set_actor_scale3d(unreal.Vector(*scale))
                    actor.set_actor_label(d['label']);actor.set_folder_path('PK01/'+data['project']+'/'+d['category']);prop(actor,'tags',[unreal.Name(scene_tag),unreal.Name(OWNER)])
                    if d['category'] in ('Water','Foliage','Lighting'):
                        actor.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
                for actor in previous:api.destroy_actor(actor)
        except Exception:
            for actor in spawned:
                try:api.destroy_actor(actor)
                except Exception:pass
            raise
    report=dict(engine_version=unreal.SystemLibrary.get_engine_version(),basis=basis,meshes=len(meshes),actors=len(spawned),warnings=WARNINGS,level_saved=False)
    (ROOT/'PK01_last_unreal_run.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    log(f'Created {len(spawned)} actors sharing {len(meshes)} static meshes. Inspect collisions/materials, then save the level manually.')
    log('For many trees use Actor > Merge Actors > Batch or Foliage Mode after inspection. No automatic HISM conversion was applied.')

if __name__=='__main__':
    try:main()
    except Exception:
        unreal.log_error('[PK01] Stopped: '+traceback.format_exc());raise
