"""Deterministic masterplan generator, landscape exclusion and SW01 path adapter.
No numpy/shapely/pip dependencies. All plans are calculated before Blender is edited.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict,replace
import math,random
from .geometry import Mesh,MAT,ScenePlan,Port,rect,ellipse,arc,from_sw01,TAU,transform
from .vendor import sw01_core as sw
from . import sports,props,flow,curves

@dataclass
class ParkConfig:
    preset:str='CAMPUS'
    scene_name:str='PK01_Aster_Park'
    seed:int=41
    height:float=.18
    path_width:float=3.2
    path_pattern:str='SLABS'
    paver_length:float=.80
    paver_width:float=.40
    joint:float=.006
    border_width:float=.12
    tactile:bool=False
    variation:float=.075
    paver_tint:tuple=(.94,.96,.96)
    curb_tint:tuple=(1.,1.,1.)
    border_tint:tuple=(.32,.35,.39)
    detail:str='BALANCED'
    tree_count:int=140
    tree_spacing:float=4.8
    tree_scale:float=1.
    pond:bool=True
    forest:bool=True
    furniture:bool=True
    gardens:bool=True
    lights:bool=True
    fencing:bool=True
    basketball:bool=True
    tennis:bool=True
    volleyball:bool=True
    futsal:bool=True
    badminton:bool=True
    pickleball:bool=True
    table_tennis:bool=True
    fitness:bool=True
    football:bool=True
    running_track:bool=True
    track_lanes:int=6
    pond_depth:float=2.2
    palette:str='COASTAL'
    path_style:str='FLOW'
    curb_profile:str='BULLNOSE'
    junction_radius:float=2.5
    meander:float=1.2
    def validate(self):
        if self.preset not in ('CAMPUS','COMMUNITY','GARDEN'):raise ValueError('Unknown park preset.')
        if self.detail not in ('DRAFT','BALANCED','HERO'):raise ValueError('Unknown detail level.')
        for n in ('height','path_width','paver_length','paver_width','joint','variation','tree_spacing','tree_scale','pond_depth'):
            if not math.isfinite(float(getattr(self,n))):raise ValueError('Non-finite '+n)
        if not .08<=self.height<=.40:raise ValueError('Walking surface height: 0.08..0.40 m.')
        if not 2.0<=self.path_width<=5.:raise ValueError('Masterplan path width: 2..5 m.')
        if not 0<=self.tree_count<=550:raise ValueError('Tree count: 0..550.')
        if not 3<=self.tree_spacing<=15:raise ValueError('Tree spacing: 3..15 m.')
        if not .5<=self.tree_scale<=1.6:raise ValueError('Tree scale: .5..1.6.')
        if not .6<=self.pond_depth<=4:raise ValueError('Pond depth: .6..4 m.')
        if self.track_lanes not in range(2,9):raise ValueError('Track lanes: 2..8.')
        if self.path_style not in ('CLASSIC','FLOW'):raise ValueError('Unknown path style.')
        if self.curb_profile not in flow.modeling.CURB_STYLES:raise ValueError('Unknown curb profile.')
        for n in ('junction_radius','meander'):
            if not math.isfinite(float(getattr(self,n))):raise ValueError('Non-finite '+n)
        if not 0<=self.junction_radius<=6:raise ValueError('Junction curb-return radius: 0..6 m.')
        if not 0<=self.meander<=4:raise ValueError('Path meander: 0..4 m.')
        sw_config(self,self.path_width).validate()
        return self

def sw_config(c,width=None,curb_left=True,curb_right=True):
    return sw.Config(width=width or c.path_width,height=c.height,pattern=c.path_pattern,
        pattern_angle=45. if c.path_pattern=='HERRINGBONE' else 0.,paver_length=c.paver_length,
        paver_width=c.paver_width,joint=c.joint,bevel=.003,curb_left=curb_left,curb_right=curb_right,
        border_width=c.border_width,tactile=c.tactile,variation=c.variation,paver_tint=tuple(c.paver_tint),
        curb_tint=tuple(c.curb_tint),border_tint=tuple(c.border_tint),curve_step=.40,
        max_pavers=24000,seed=c.seed)

def distance_segment(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];ll=dx*dx+dy*dy
    if ll<1e-12:return math.dist(p,a)
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/ll))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def blocked(p,reservations,margin=0):
    for r in reservations:
        t=r['type']
        if t=='rect':
            a=math.radians(-r.get('yaw',0));x,y=p[0]-r['x'],p[1]-r['y'];xx=x*math.cos(a)-y*math.sin(a);yy=x*math.sin(a)+y*math.cos(a)
            if abs(xx)<=r['l']/2+margin and abs(yy)<=r['w']/2+margin:return True
        elif t=='ellipse':
            if ((p[0]-r['x'])/(r['rx']+margin))**2+((p[1]-r['y'])/(r['ry']+margin))**2<=1:return True
        elif t=='capsule':
            if distance_segment(p,(r['x']-r['straight']/2,r['y']),(r['x']+r['straight']/2,r['y']))<=r['r']+margin:return True
        elif t=='path':
            box=r.get('bbox')
            if box:
                pad=r['width']/2+margin
                if p[0]<box[0]-pad or p[0]>box[2]+pad or p[1]<box[1]-pad or p[1]>box[3]+pad:continue
            if any(distance_segment(p,a,b)<=r['width']/2+margin for a,b in zip(r['points'],r['points'][1:])):return True
    return False

def reserve_rect(plan,x,y,l,w,label,yaw=0):
    plan.reservations.append(dict(type='rect',x=x,y=y,l=l,w=w,label=label,yaw=yaw))

def flowing(c):return getattr(c,'path_style','CLASSIC')=='FLOW'

def add_path(plan,c,name,points,width=None,curbs=True,junction=False,tangents=(None,None)):
    """CLASSIC: the unmodified SW01 1.0.1 mesher. FLOW: PK01 path-following paving and
    swept curbs built on the same SW01 Path/prism/material contract."""
    cfg=sw_config(c,width,curbs,curbs)
    if junction:cfg=replace(cfg,border_width=0,tactile=False)
    if flowing(c) and not junction and len(points)>2:
        points=curves.resample_adaptive(points,max_step=.45,min_step=.15)
    origin=points[0];local=[(p[0]-origin[0],p[1]-origin[1]) for p in points]
    path=flow.make_path(local,*tangents) if flowing(c) and not junction else sw.Path(local)
    if flowing(c) and not junction:
        mesh,meta=flow.build_flow_module('SM_PK01_Flow_'+name,path,cfg,c.curb_profile)
    else:
        mesh,meta=sw.build_module('SM_PK01_SW01_'+name,path,cfg)
        mesh=from_sw01(mesh,meta)
    zone=plan.zone('Path_'+name,(origin[0],origin[1],0),category='Paths')
    plan.place(mesh,zone=zone,category='Paths')
    plan.paths.append(dict(name=name,points=[tuple(p) for p in points],width=cfg.width,height=cfg.height,junction=junction))
    bbox=(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
    plan.reservations.append(dict(type='path',points=[tuple(p) for p in points],width=cfg.width,label=name,bbox=bbox))
    for tag in ('in','out'):
        port=meta[tag]
        plan.ports.append(Port(name+'_'+tag.upper(),tuple(port['location']),port['yaw_degrees'],cfg.width,cfg.height,zone))
    return mesh

JUNCTION_EXTENSION=.30  # straight curb after a curb return, before the arm mouth

def junction_reach(c,nodes,edges):
    """Per-node distance from junction centre to arm mouths.
    CLASSIC: half width (square pad). FLOW: half width + curb-return radius + a short
    straight, with the radius reduced locally where neighbouring junctions are close.
    """
    half=c.path_width/2
    if not flowing(c):return {k:half for k in nodes},{k:0. for k in nodes}
    budget={k:float(c.junction_radius)+JUNCTION_EXTENSION for k in nodes}
    for a,b in edges:
        avail=(math.dist(nodes[a],nodes[b])-.45)/2-half
        budget[a]=min(budget[a],avail);budget[b]=min(budget[b],avail)
    reach={};fillet={}
    for k,b in budget.items():
        if b<.05:raise ValueError('Junctions are too close for FLOW paths. Use CLASSIC or a narrower path.')
        ext=min(JUNCTION_EXTENSION,b);r=b-ext
        fillet[k]=r if r>=.3 else 0.;reach[k]=half+fillet[k]+ext
    return reach,fillet

def grid_network(plan,c,nodes,edges):
    """Orthogonal junction network. CLASSIC: square flush pads + trimmed straight paths.
    FLOW: links meander gently between rounded junctions (built by finish_junctions).
    Returns the per-node arm reach so spurs end exactly on a junction mouth."""
    half=c.path_width/2;reach,fillet=junction_reach(c,nodes,edges)
    if flowing(c):plan.settings['_junctions']={k:dict(xy=tuple(v),reach=reach[k],fillet=fillet[k]) for k,v in nodes.items()}
    else:
        for key,(x,y) in nodes.items():
            add_path(plan,c,'Node_'+key,[(x-half,y),(x+half,y)],curbs=False,junction=True)
    for i,(a,b) in enumerate(edges):
        p,q=nodes[a],nodes[b];dx,dy=q[0]-p[0],q[1]-p[1];L=math.hypot(dx,dy)
        if min(abs(dx),abs(dy))>.001:raise ValueError('Preset junctions must be orthogonal.')
        if L<=reach[a]+reach[b]+.4:raise ValueError('Junctions are too close.')
        u=(dx/L,dy/L)
        start=(p[0]+u[0]*reach[a],p[1]+u[1]*reach[a]);end=(q[0]-u[0]*reach[b],q[1]-u[1]*reach[b])
        points=[start,end]
        if flowing(c) and c.meander>0:
            span=math.dist(start,end);waves=1 if span<55 else 2
            amp=curves.safe_meander_amplitude(span,c.path_width,waves,c.meander)
            # Alternate the bow side so a long spine reads as one continuous S-line.
            if amp>=.15:points=curves.meander(start,end,amp,waves,.3,1. if i%2==0 else -1.)
        add_path(plan,c,f'Link_{i:02d}',points,tangents=(u,u))
    return reach

def finish_junctions(plan,c):
    """FLOW: build one rounded junction per node once all arms are known."""
    nodes=plan.settings.pop('_junctions',None)
    if not nodes:return
    cfg=replace(sw_config(c,None,True,True),tactile=False);cache={}
    ends=[(p['points'][0],p['points'][-1]) for p in plan.paths if not p['junction']]
    for key,n in nodes.items():
        (x,y),reach=n['xy'],n['reach']
        arms=''.join(d for d,(dx,dy) in flow.DIRECTIONS.items()
                     if any(math.dist(e,(x+dx*reach,y+dy*reach))<.05 for pair in ends for e in pair))
        arms=''.join(d for d in flow.ORDER if d in arms)
        name=f'SM_PK01_FlowJunction_{arms or "Pad"}_{round(reach*100)}_{round(n["fillet"]*100)}_{c.curb_profile[:2]}'
        if name not in cache:cache[name]=flow.build_junction(name,arms,cfg,reach,n['fillet'],curb_style=c.curb_profile)[0]
        zone=plan.zone('Junction_'+key,(x,y,0),category='Paths')
        plan.place(cache[name],zone=zone,category='Paths')
        if c.furniture and len(arms)>=3:corner_benches(plan,c,(x,y),arms,n['fillet'])
        plan.paths.append(dict(name='Node_'+key,points=[(x-reach,y),(x+reach,y)],width=2*reach,height=c.height,junction=True))
        reserve_rect(plan,x,y,2*reach,2*reach,'Junction_'+key)

def corner_benches(plan,c,centre,arms,fillet,angle=70.):
    """Curved benches nested in the grass of each curb return, facing the junction."""
    if fillet<2.:return
    half=c.path_width/2;radius=fillet-.75;bench=None
    for i,d in enumerate(flow.ORDER):
        nxt=flow.ORDER[(i+1)%4]
        if d not in arms or nxt not in arms:continue
        (dx,dy),(px,py)=flow.DIRECTIONS[d],flow.DIRECTIONS[nxt]
        fc=(centre[0]+(dx+px)*(half+fillet),centre[1]+(dy+py)*(half+fillet))
        face=math.atan2(-(dy+py),-(dx+px))
        probes=[(fc[0]+radius*math.cos(face+a),fc[1]+radius*math.sin(face+a)) for a in (-math.radians(angle/2),0.,math.radians(angle/2))]
        if any(blocked(q,plan.reservations,.45) for q in probes):continue
        bench=bench or props.bench_curved(radius,angle)
        plan.place(bench,(fc[0],fc[1],0.),math.degrees(face),category='Furniture')
        mid=probes[1];reserve_rect(plan,mid[0],mid[1],1.6,1.6,'Seat')

def add_facility(plan,c,kind,center,name=None,yaw=0,infield=False):
    facility=sports.create(kind,c.height,c.fencing,gate_width=c.path_width+.4,infield=infield)
    name=name or kind.title();zone=plan.zone(name,(*center,0),yaw,'Sports',kind=kind,size=facility.size)
    for mesh,loc,rot in facility.components:
        if mesh.vertices:plan.place(mesh,loc,rot,zone=zone,category='Sports')
    port=Port(name+'_ENTRY',(0,facility.size[1]/2,0),90,c.path_width,c.height,zone)
    plan.ports.append(port)
    reserve_rect(plan,*center,*facility.size,name,yaw)
    plan.notes.extend(facility.notes)
    return facility

def pond_shape(rx,ry,n=96):return ellipse(rx,ry,n,irregular=.065)
def pond_radius(theta):return 1+.065*(.65*math.sin(3*theta+.4)+.35*math.sin(5*theta-1.1))
def ground_height(x,y,ponds):
    z=0.
    for d in ponds:
        nx,ny=(x-d['x'])/d['rx'],(y-d['y'])/d['ry'];rho=math.hypot(nx,ny)/pond_radius(math.atan2(ny,nx))
        if rho<1.10:
            t=max(0,min(1,(rho-.20)/.90));smooth=t*t*(3-2*t)
            z=min(z,-d['depth']*(1-smooth))
    return z

def add_terrain(plan,c,size,ponds):
    l,w=size;m=Mesh('SM_PK01_Terrain_'+c.preset+'_'+str(c.seed));step=3. if c.detail=='DRAFT' else 2.
    nx=math.ceil(l/step);ny=math.ceil(w/step)
    for j in range(ny+1):
        y=-w/2+w*j/ny
        for i in range(nx+1):
            x=-l/2+l*i/nx;z=ground_height(x,y,ponds)
            m.vertices.append((x,y,z))
            # Low amplitude tint variation to break repetition without camouflage patches.
            v=1+.06*math.sin(x*.11+math.cos(y*.07))+.035*math.sin(y*.28-x*.05)
            m.colors.append((v,v,.94*v))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;d=a+nx+1;cc=d+1
            for tri in ((a,b,cc),(a,cc,d)):
                # Soil bowl; a grass plane never cuts through the water surface.
                center=tuple(sum(m.vertices[k][axis] for k in tri)/3 for axis in range(3))
                mat=MAT['Soil'] if center[2]<-.08 else MAT['Grass']
                m.face(tri,tuple((m.vertices[k][0]/3,m.vertices[k][1]/3) for k in tri),mat)
    m.smooth=[True]*len(m.triangles);m.surface_only=True
    m.meta['complex_collision']=True
    plan.place(m,category='Terrain')


def add_pond(plan,c,d):
    rx,ry=d['rx'],d['ry'];x,y=d['x'],d['y'];zone=plan.zone('Lake',(x,y,0),category='Water')
    m=Mesh(f'SM_PK01_PondWater_{rx:g}_{ry:g}');m.surface_only=True
    # Radius .94 is completely inside the depressed terrain bowl.
    # No claim of a simulated WaterBody; exported separately for UE water replacement.
    m.plane(pond_shape(rx*.94,ry*.94),-.10,MAT['Water'],uvscale=1.7)
    m.meta['water']=True;plan.place(m,zone=zone,category='Water')
    plan.reservations.append(dict(type='ellipse',x=x,y=y,rx=rx*1.10,ry=ry*1.10,label='Lake'))
    rocks=[props.rock(i) for i in range(5)];reeds=[props.reed(i) for i in range(3)];rng=random.Random(c.seed+80)
    outline=pond_shape(rx*1.04,ry*1.04,95)
    for i,(px,py) in enumerate(outline):
        # Keep the west jetty mouth clear.
        if px < -rx*.72 and abs(py)<3.6:continue
        s=rng.uniform(.8,1.6);z=ground_height(x+px,y+py,[d])-.04
        plan.place(rocks[i%5],(px,py,z),rng.uniform(0,360),(s,s,s),zone,'Landscape')
        if i%2==0:
            px*=.99;py*=.99;z=ground_height(x+px,y+py,[d])
            plan.place(reeds[i%3],(px,py,z),rng.uniform(0,360),zone=zone,category='Foliage')
    # Timber viewing jetty: open entry, rails on exposed outer edges only.
    length=min(16.,rx*.73);width=4.4;start=-rx-2.;jet=Mesh('SM_PK01_Jetty_'+c.preset)
    for i in range(math.ceil(length/.15)):
        xx=start+(i+.5)*length/math.ceil(length/.15)
        jet.box((xx,0,c.height-.04),(length/math.ceil(length/.15)-.008,width,.08),MAT['Timber'],.004,uvscale=.7)
    for yy in (-width/2+.2,width/2-.2):
        jet.box((start+length/2,yy,c.height-.19),(length,.14,.22),MAT['Steel'],.006)
        for i in range(math.ceil(length/2)+1):
            xx=start+i*length/math.ceil(length/2)
            jet.cylinder((xx,yy,-d['depth']),(xx,yy,c.height),.095,MAT['Steel'],n=8)
            if i>2:jet.cylinder((xx,yy,c.height),(xx,yy,c.height+1.05),.024,MAT['Steel'],n=8)
        jet.cylinder((start+length*.38,yy,c.height+1.05),(start+length,yy,c.height+1.05),.028,MAT['Steel'],n=8)
    jet.add_collision_box((start+length/2,0,c.height-.05),(length,width,.10))
    # Collision rails only where rail geometry exists.
    for yy in (-width/2+.2,width/2-.2):jet.add_collision_box((start+length*.69,yy,c.height+.52),(length*.62,.07,1.05))
    plan.place(jet,zone=zone,category='Architecture')
    reserve_rect(plan,x+start+length/2,y,length,width,'Jetty')
    plan.ports.append(Port('Lake_ENTRY',(start,0,0),180,c.path_width,c.height,zone))
    return (x+start,y)


def add_furniture(plan,c,spine_y,xlimits,ponds):
    if not c.furniture:return
    b=props.bench();p=props.planter();binm=props.bin_prop();bike=props.bike_rack()
    rng=random.Random(c.seed+61)
    for x in range(math.ceil(xlimits[0]/15)*15,int(xlimits[1]),15):
        y=spine_y+c.path_width/2+1.3
        if blocked((x,y),plan.reservations,1.):continue
        # Seating on a discrete, level pad rather than floating above grass.
        pad=Mesh(f'SM_PK01_BenchPad_{round(c.height*1000)}');pad.box((0,0,c.height/2),(3.,1.6,c.height),MAT['Curb'],.015)
        plan.place(pad,(x,y,0),category='Furniture');plan.place(b,(x,y,c.height),category='Furniture')
        reserve_rect(plan,x,y,3.2,2.,'Seat')
        if x%30==0:plan.place(binm,(x+2.,y,c.height*.1),category='Furniture')
    if c.gardens:
        for x in range(math.ceil(xlimits[0]/30)*30,int(xlimits[1]),30):
            y=spine_y-c.path_width/2-3.1
            if blocked((x,y),plan.reservations,2.):continue
            plan.place(p,(x,y,0),category='Gardens');reserve_rect(plan,x,y,4.4,2.,'Planter')
            for xx in (-1.35,-.45,.45,1.35):
                plan.place(props.shrub(1,True),(x+xx,y,.41),rng.uniform(0,360),(.85,.85,.85),category='Foliage')
    plan.place(bike,(xlimits[1]-4,spine_y-5,0),90,category='Furniture')


def add_lights(plan,c,size):
    if not c.lights:return
    mesh=props.light_pole()
    for p in plan.paths:
        if p['junction']:continue
        if flowing(c):
            # Follow the real centre line so poles keep their setback on curves.
            pts=p['points'];dist=curves.cumulative(pts);length=dist[-1]
            if length<10:continue
            n=max(1,int(length/16));off=p['width']/2+.8
            for j in range(n):
                (x,y),t=curves.sample(pts,(j+.5)*length/n,dist);x-=t[1]*off;y+=t[0]*off
                if blocked((x,y),plan.reservations,.25):continue
                plan.place(mesh,(x,y,0),math.degrees(math.atan2(-t[0],t[1])),category='Lighting')
                reserve_rect(plan,x,y,.6,.6,'Light')
            continue
        if len(p['points'])>20:continue
        a,b=p['points'][0],p['points'][-1];length=math.dist(a,b)
        if length<10:continue
        dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
        for j in range(max(1,int(length/16))):
            t=(j+.5)/max(1,int(length/16));off=p['width']/2+.8
            x=a[0]+t*(b[0]-a[0])-dy*off;y=a[1]+t*(b[1]-a[1])+dx*off
            if blocked((x,y),plan.reservations,.25):continue
            plan.place(mesh,(x,y,0),math.degrees(math.atan2(-dx,dy)),category='Lighting')
            reserve_rect(plan,x,y,.6,.6,'Light')


def scatter_forest(plan,c,size,ponds):
    if not c.forest or c.tree_count==0:return
    rng=random.Random(c.seed);l,w=size;placed=[]
    variants=[props.tree('BROADLEAF',41,c.detail),props.tree('BROADLEAF',63,c.detail),props.tree('BIRCH',22,c.detail),props.tree('CYPRESS',7,c.detail)]
    # Entire procedural crown clears reserved paths/courts, not just the trunk.
    radii={m.name:max(math.hypot(v[0],v[1]) for v in m.vertices) for m in variants}
    crown_records=[]
    # Rejection sampling with a measured minimum distance, capped deterministically.
    grid={};cell=c.tree_spacing
    for attempt in range(c.tree_count*180):
        if len(placed)>=c.tree_count:break
        x=rng.uniform(-l/2+4,l/2-4);y=rng.uniform(-w/2+4,w/2-4)
        # Emphasise the forest belt and garden, leave readable sunny gaps.
        edge=min(l/2-abs(x),w/2-abs(y))
        if edge>18 and rng.random()<.38:continue
        scale=c.tree_scale*rng.uniform(.78,1.16);proto=variants[rng.randrange(len(variants))]
        clearance=radii[proto.name]*scale+.35
        if blocked((x,y),plan.reservations,clearance):continue
        gx,gy=math.floor(x/cell),math.floor(y/cell)
        if any(math.hypot(x-q[0],y-q[1])<c.tree_spacing for ix in range(gx-1,gx+2) for iy in range(gy-1,gy+2) for q in grid.get((ix,iy),())):continue
        grid.setdefault((gx,gy),[]).append((x,y));placed.append((x,y))
        crown_records.append((x,y,clearance))
        plan.place(proto,(x,y,ground_height(x,y,ponds)),rng.uniform(0,360),(scale,scale,scale),category='Trees')
        if c.gardens and len(placed)%3==0:
            bush=props.shrub(len(placed)%2)
            plan.place(bush,(x+.9,y+.6,ground_height(x+.9,y+.6,ponds)),rng.uniform(0,360),category='Foliage')
    if len(placed)<c.tree_count:plan.notes.append(f'Tree placement filled {len(placed)}/{c.tree_count}; exclusions and spacing were preserved.')
    plan.settings['tree_points']=placed
    plan.settings['tree_crown_clearances']=crown_records


def cubic(p0,p1,p2,p3,step=.4):
    n=max(8,math.ceil((math.dist(p0,p1)+math.dist(p1,p2)+math.dist(p2,p3))/step))
    return [tuple((1-t)**3*p0[j]+3*(1-t)**2*t*p1[j]+3*(1-t)*t*t*p2[j]+t**3*p3[j] for j in range(2)) for t in (i/n for i in range(n+1))]


def build_park(c:ParkConfig):
    c.validate();plan=ScenePlan(c.scene_name);plan.settings=asdict(c)
    h=c.path_width/2;ponds=[]
    def lead(p0,p1):
        # FLOW: the first Bezier handle leaves a junction mouth exactly along the arm.
        return (p1[0],p0[1]) if flowing(c) else p1
    def along(p0,p1):return ((p1[0]-p0[0],p1[1]-p0[1]),None)
    if c.preset=='CAMPUS':
        size=(270.,224.);main_y=-31.;center=(-34.,29.)
        if c.running_track:
            track,lines,dim,meta=sports.track(400.,c.track_lanes,c.height,c.detail)
            zone=plan.zone('RunningTrack',(*center,0),category='Sports',kind='TRACK',**meta)
            plan.place(track,zone=zone,category='Sports');plan.place(lines,zone=zone,category='Sports')
            plan.reservations.append(dict(type='capsule',x=center[0],y=center[1],straight=meta['straight_m'],r=meta['inner_radius_m']+c.track_lanes*1.22,label='Track'))
        if c.football:add_facility(plan,c,'FOOTBALL',center,infield=c.running_track)
        row=[('BASKETBALL',-99.),('TENNIS',-58.),('VOLLEYBALL',-21.),('FUTSAL',22.),('FITNESS',91.)]
        nodes={'West':(-124.,main_y),'East':(116.,main_y),'LakeCorner':(62.,main_y),'North':(62.,84.)}
        for kind,x in row:
            if getattr(c,kind.lower()):nodes[kind]=(x,main_y)
        if c.running_track or c.football:nodes['Track']=(-34.,main_y)
        lower=[('BADMINTON',-67.),('PICKLEBALL',-39.),('TABLE_TENNIS',-12.)]
        enabled=[(k,x) for k,x in lower if getattr(c,k.lower())]
        if enabled:
            nodes['LowerWest']=(-89.,-82.);nodes['LowerEast']=(116.,-82.)
            for kind,x in enabled:nodes['Lower_'+kind]=(x,-82.)
        if c.pond:
            d=dict(x=95.,y=34.,rx=24.,ry=18.,depth=c.pond_depth);ponds=[d];nodes['LakeDock']=(62.,34.)
        edges=[]
        main=sorted([k for k,v in nodes.items() if v[1]==main_y],key=lambda k:nodes[k][0])
        edges.extend(zip(main,main[1:]));vertical=['LakeCorner']+(['LakeDock'] if c.pond else [])+['North'];edges.extend(zip(vertical,vertical[1:]))
        if enabled:
            lowerkeys=sorted([k for k,v in nodes.items() if v[1]==-82.],key=lambda k:nodes[k][0])
            edges.extend(zip(lowerkeys,lowerkeys[1:]));edges.append(('LowerEast','East'))
        R=grid_network(plan,c,nodes,list(edges))
        for kind,x in row:
            if not getattr(c,kind.lower()):continue
            f=add_facility(plan,c,kind,(x,-59.));entry=-59.+f.size[1]/2
            add_path(plan,c,'Entry_'+kind,[(x,entry),(x,main_y-R[kind])])
        for kind,x in enabled:
            f=add_facility(plan,c,kind,(x,-98.));entry=-98.+f.size[1]/2
            add_path(plan,c,'Entry_'+kind,[(x,entry),(x,-82.-R['Lower_'+kind])])
        if c.running_track:
            add_path(plan,c,'Track_Approach',[(-34.,main_y+R['Track']),(-34.,center[1]-dim[1]/2)])
        elif c.football:
            add_path(plan,c,'Pitch_Approach',[(-34.,main_y+R['Track']),(-34.,center[1]-37.)])
        if c.pond:
            entry=add_pond(plan,c,d);add_path(plan,c,'Lake_Approach',[(62+R['LakeDock'],34),entry])
        # Gentle curved upper promenade: open curve, safely above the track.
        p0=(62-R['North'],84);p1=lead(p0,(25,87));add_path(plan,c,'Woodland_Curve',cubic(p0,p1,(-60,92),(-122,86)),tangents=along(p0,p1))
        xlimits=(-116,112)
    elif c.preset=='COMMUNITY':
        size=(164.,144.);main_y=-24.;nodes={'West':(-75.,main_y),'East':(74.,main_y),'Spur':(25.,main_y),'North':(25.,60.)}
        rows=[('BASKETBALL',-54.),('TENNIS',-11.),('VOLLEYBALL',31.),('FITNESS',61.)]
        for kind,x in rows:
            if getattr(c,kind.lower()):nodes[kind]=(x,main_y)
        if c.running_track:nodes['TrackEntry']=(-29.,main_y)
        if c.pond:
            d=dict(x=53.,y=26.,rx=18.,ry=15.,depth=c.pond_depth);ponds=[d];nodes['LakeDock']=(25.,26.)
        main=sorted([k for k,v in nodes.items() if v[1]==main_y],key=lambda k:nodes[k][0])
        edges=list(zip(main,main[1:]));vertical=['Spur']+(['LakeDock'] if c.pond else [])+['North'];edges+=list(zip(vertical,vertical[1:]))
        R=grid_network(plan,c,nodes,edges)
        for kind,x in rows:
            if not getattr(c,kind.lower()):continue
            f=add_facility(plan,c,kind,(x,-48.));add_path(plan,c,'Entry_'+kind,[(x,-48.+f.size[1]/2),(x,main_y-R[kind])])
        if c.running_track:
            tr,ln,dim,meta=sports.track(200.,min(c.track_lanes,4),c.height,c.detail);zone=plan.zone('RunningTrack',(-29.,28.,0),category='Sports',kind='TRACK',**meta)
            plan.place(tr,zone=zone,category='Sports');plan.place(ln,zone=zone,category='Sports')
            plan.reservations.append(dict(type='capsule',x=-29.,y=28.,straight=meta['straight_m'],r=meta['inner_radius_m']+min(c.track_lanes,4)*1.22,label='Track'))
            add_path(plan,c,'Track_Approach',[(-29.,main_y+R['TrackEntry']),(-29.,28.-dim[1]/2)])
        if c.pond:
            entry=add_pond(plan,c,d);add_path(plan,c,'Lake_Approach',[(25+R['LakeDock'],26),entry])
        p0=(25-R['North'],60);p1=lead(p0,(3,65));add_path(plan,c,'Woodland_Curve',cubic(p0,p1,(-45,65),(-74,58)),tangents=along(p0,p1))
        plan.notes.append('Community preset uses a 200 m recreational loop (maximum 4 lanes); football and secondary sports are added separately.')
        xlimits=(-69,68)
    else:
        size=(142.,112.);main_y=-27.;nodes={'West':(-62.,main_y),'East':(61.,main_y),'Spur':(-8.,main_y),'North':(-8.,47.)}
        if c.pond:
            d=dict(x=29.,y=17.,rx=24.,ry=18.,depth=c.pond_depth);ponds=[d];nodes['LakeDock']=(-8.,17.)
        rows=[('BASKETBALL',-44.,11.),('TENNIS',-43.,-46.)]
        # Basketball entrance is south-facing so it connects to the lower spine.
        if c.basketball:nodes['BasketEntry']=(-44.,main_y)
        if c.tennis:nodes['TennisEntry']=(-43.,main_y)
        # Adjacent x=-44/-43 junctions would clash: use a shared node and a short curve.
        if c.basketball and c.tennis:del nodes['TennisEntry']
        main=sorted([k for k,v in nodes.items() if v[1]==main_y],key=lambda k:nodes[k][0])
        edges=list(zip(main,main[1:]));vertical=['Spur']+(['LakeDock'] if c.pond else [])+['North'];edges+=list(zip(vertical,vertical[1:]))
        R=grid_network(plan,c,nodes,edges)
        if c.basketball:
            f=add_facility(plan,c,'BASKETBALL',(-44.,11.),yaw=180)
            add_path(plan,c,'Basket_Approach',[(-44.,main_y+R['BasketEntry']),(-44.,11.-f.size[1]/2)])
        if c.tennis:
            # Court centred on the shared entry x coordinate for exact flush joins.
            x=-44. if c.basketball else -43.
            key='BasketEntry' if c.basketball else 'TennisEntry'
            f=add_facility(plan,c,'TENNIS',(x,-46.));add_path(plan,c,'Tennis_Approach',[(x,-46.+f.size[1]/2),(x,main_y-R[key])])
        if c.pond:
            entry=add_pond(plan,c,d);add_path(plan,c,'Lake_Approach',[(-8+R['LakeDock'],17),entry])
        p0=(-8+R['North'],47);p1=lead(p0,(10,50));add_path(plan,c,'Garden_Curve',cubic(p0,p1,(38,50),(62,43)),tangents=along(p0,p1))
        plan.notes.append('Garden preset contains basketball and tennis only; other facilities can be added at the cursor.')
        xlimits=(-55,55)
    finish_junctions(plan,c)
    plan.settings['site_size_m']=size;plan.settings['ponds']=ponds
    add_terrain(plan,c,size,ponds)
    if c.furniture:
        # An entrance lounge pavilion deliberately separated from all court reservations.
        center=(size[0]/2-35,main_y-10)
        if not blocked(center,plan.reservations,5.5):
            pad=Mesh('SM_PK01_LoungePad_'+c.preset);pad.box((0,0,c.height/2),(8.,7.,c.height),MAT['Curb'],.015)
            plan.place(pad,(*center,0),category='Furniture');plan.place(props.pergola(),(*center,c.height),category='Furniture')
            plan.place(props.picnic(),(*center,c.height),category='Furniture');reserve_rect(plan,*center,8.,7.,'Lounge')
    add_furniture(plan,c,main_y,xlimits,ponds);add_lights(plan,c,size);scatter_forest(plan,c,size,ponds)
    plan.notes.extend(['Original procedural tree/texture starters, not photogrammetry.','Flat masterplan with a depressed pond basin; no terrain draping or automatic UE WaterBody.','Sports markings are visual references, not competition or accessibility certification.'])
    return plan
