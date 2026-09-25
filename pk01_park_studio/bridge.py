"""Connection tools for PK01 ports and original SW01 1.0.1 socket empties."""
import bpy,math,json
from mathutils import Vector
from dataclasses import fields,replace
from .vendor import sw01_core as sw
from .geometry import ScenePlan,from_sw01,Port
from .planner import ParkConfig,sw_config,cubic

def port_info(obj,prefer='OUT'):
    if not obj:raise ValueError('Choose both connection endpoints.')
    if obj.type=='MESH':
        candidates=[o for o in obj.children if o.type=='EMPTY' and o.name.upper().endswith(prefer)]
        if not candidates:raise ValueError('Choose an IN/OUT socket Empty, not the mesh. This mesh has no matching child socket.')
        obj=candidates[0]
    if obj.type!='EMPTY':raise ValueError('A connection endpoint must be an Empty socket.')
    scale=obj.matrix_world.to_scale()
    if any(abs(v-1)>1e-4 for v in scale):raise ValueError('Socket scale must be 1. Apply transforms to the source module first.')
    direction=obj.matrix_world.to_3x3()@Vector((1,0,0))
    if abs(direction.z)>.001:raise ValueError('Tilted sockets are unsupported. Keep connector directions in the XY plane.')
    pos=tuple(obj.matrix_world.translation);angle=math.atan2(direction.y,direction.x)
    cfg=None;parent=obj.parent
    while parent:
        if parent.get('sw01_meta'):
            cfg=json.loads(parent['sw01_meta']).get('config');break
        parent=parent.parent
    width=float(obj.get('pk01_width',cfg['width'] if cfg else 0))
    height=float(obj.get('pk01_height',cfg['height'] if cfg else 0))
    if width<=0 or height<=0:raise ValueError('Unrecognised socket. Use a PK01 port or a socket parented to a SW01-generated mesh.')
    role=obj.get('pk01_role','OUT' if obj.name.upper().endswith('OUT') else 'IN')
    return dict(object=obj,position=pos,heading=angle,width=width,height=height,config=cfg,role=role)

def connection_plan(a,b,c,handle=0.,flip_start=False,flip_end=False):
    pa,pb=port_info(a,'OUT'),port_info(b,'IN')
    if pa['object']==pb['object']:raise ValueError('Choose two different sockets.')
    if abs(pa['width']-pb['width'])>.002 or abs(pa['height']-pb['height'])>.002:
        raise ValueError('Endpoint width / height mismatch. Match dimensions first; this tool does not stretch a junction.')
    p0,p3=pa['position'],pb['position'];distance=math.dist(p0[:2],p3[:2])
    if distance<.5 or distance>250:raise ValueError('Connection distance must be .5..250 m.')
    h=handle if handle>0 else min(distance*.33,15.)
    ah=pa['heading']+(math.pi if flip_start else 0.)
    # ENTRY ports point outward; the connector approaches against their outward normal.
    bh=pb['heading']+(math.pi if pb['role'] in ('ENTRY','OUT') else 0.)+(math.pi if flip_end else 0.)
    p1=(p0[0]+h*math.cos(ah),p0[1]+h*math.sin(ah));p2=(p3[0]-h*math.cos(bh),p3[1]-h*math.sin(bh))
    points=cubic(p0[:2],p1,p2,p3[:2],.4);local=[(x-p0[0],y-p0[1]) for x,y in points]
    if pa['config']:
        known={f.name for f in fields(sw.Config)};cfg=sw.Config(**{k:v for k,v in pa['config'].items() if k in known})
    else:cfg=sw_config(c,pa['width'])
    cfg=replace(cfg,width=pa['width'],height=pa['height'],end_elevation=p3[2]-p0[2],curve_step=.4)
    path=sw.Path(local);path.normals[0]=(-math.sin(ah),math.cos(ah));path.normals[-1]=(-math.sin(bh),math.cos(bh))
    name='SW_Link';mesh,meta=sw.build_module('SM_PK01_SW01_Connector',path,cfg)
    plan=ScenePlan('PK01_Connector');plan.settings={'palette':c.palette};plan.zone(name,p0,category='Paths')
    plan.place(from_sw01(mesh,meta),zone=name,category='Paths')
    for tag in ('in','out'):
        d=meta[tag];plan.ports.append(Port('Connector_'+tag.upper(),tuple(d['location']),d['yaw_degrees'],cfg.width,cfg.height,name))
    plan.notes.append('Connector is a separately editable park object; source SW01 objects are unchanged.')
    return plan

def copy_sw01_style(context,pk):
    s=getattr(context.scene,'sw01',None)
    if s is None:raise ValueError('Run the original SW01 1.0.1 script once so its SW01 panel is registered.')
    mapping={'height':'height','path_width':'width','path_pattern':'pattern','paver_length':'paver_length','paver_width':'paver_width','joint':'joint','border_width':'border_width','tactile':'tactile','variation':'variation','paver_tint':'paver_tint','curb_tint':'curb_tint','border_tint':'border_tint'}
    for target,source in mapping.items():
        if hasattr(s,source):setattr(pk,target,getattr(s,source))
    return True
