"""Sports visual layouts in metres; not homologated competition facilities.
Reference dimensions are documented in Docs/SOURCES_AND_LIMITS.md.
"""
from __future__ import annotations
from dataclasses import dataclass,field
import math
from .geometry import Mesh,MAT,rect,arc,ellipse,TAU
from . import props

SPORTS = ['BASKETBALL','TENNIS','VOLLEYBALL','BADMINTON','PICKLEBALL','FUTSAL','FOOTBALL','FITNESS','TABLE_TENNIS']
@dataclass
class Facility:
    kind:str
    size:tuple
    components:list=field(default_factory=list) # mesh, local position, yaw
    notes:list=field(default_factory=list)

def create(kind='BASKETBALL',height=.18,fencing=True,net_height=2.43,gate_width=4.4,infield=False):
    if kind not in SPORTS:raise ValueError('Unknown sport: '+kind)
    shapes={'BASKETBALL':(28.,15.,34.,21.),'TENNIS':(23.77,10.97,36.57,18.29),
            'VOLLEYBALL':(18.,9.,24.,15.),'BADMINTON':(13.40,6.10,18.,10.),
            'PICKLEBALL':(13.4112,6.096,19.5,10.5),'FUTSAL':(40.,20.,44.,24.),
            'FOOTBALL':(105.,68.,111.,74.),'FITNESS':(12.,10.,16.,14.),'TABLE_TENNIS':(9.,6.,11.,8.)}
    L,W,PL,PW=shapes[kind];h=height
    if infield and kind=='FOOTBALL':PL,PW=L,W
    suffix=('%03d'%round(h*1000))+('_Infield' if infield else '');base=Mesh('SM_PK01_'+kind+'_Base_'+suffix)
    lines=Mesh('SM_PK01_'+kind+'_Lines_'+suffix);lines.surface_only=True
    f=Facility(kind,(PL,PW));courtmat=MAT['EPDM_Teal']
    if kind=='TENNIS':courtmat=MAT['CourtBlue']
    if kind in ('FUTSAL','FOOTBALL'):courtmat=MAT['Grass']
    if kind in ('BADMINTON','PICKLEBALL'):courtmat=MAT['EPDM_Terracotta']
    base.box((0,0,h/2),(PL,PW,h),MAT['EPDM_Sage'],min(.025,h*.15))
    base.plane(rect(0,0,L,W),h+.0008,courtmat,uvscale=.7)
    base.add_collision_box((0,0,h/2),(PL,PW,h))
    f.components.append((base,(0,0,0),0));f.components.append((lines,(0,0,0),0))
    z=h+.003
    def ln(p,width=.05,close=False):lines.line(p,width,z,closed=close)
    def outline(l,w):ln(rect(0,0,l,w),close=True)
    def circ(x,y,r,start=0,end=TAU):ln(arc(x,y,r,start,end))
    if kind not in ('FITNESS','TABLE_TENNIS'):outline(L,W)
    if kind in ('BASKETBALL','FOOTBALL','FUTSAL'):ln([(0,-W/2),(0,W/2)])
    if kind=='BASKETBALL':
        circ(0,0,1.8)
        for s in (-1,1):
            bx=s*(L/2-1.575);ft=s*(L/2-5.8)
            ln([(s*L/2,-2.45),(ft,-2.45),(ft,2.45),(s*L/2,2.45)])
            circ(ft,0,1.8)
            # 6.75 m arc and the straight corner segments, no stretched markings.
            theta=math.asin(6.6/6.75);cut=bx-s*math.sqrt(6.75**2-6.6**2)
            if s==1:circ(bx,0,6.75,math.pi-theta,math.pi+theta)
            else:circ(bx,0,6.75,-theta,theta)
            for y in (-6.6,6.6):ln([(s*14,y),(cut,y)])
            f.components.append((props.hoop(),(bx,0,h),0 if s==1 else 180))
    elif kind=='TENNIS':
        for y in (-8.23/2,8.23/2):ln([(-L/2,y),(L/2,y)])
        for x in (-6.4,6.4):ln([(x,-8.23/2),(x,8.23/2)])
        ln([(-6.4,0),(6.4,0)])
        for x in (-L/2,L/2):ln([(x,0),(x-(.10 if x>0 else -.10),0)])
        f.components.append((props.net(12.8,1.07,.914),(0,0,h),0))
    elif kind=='VOLLEYBALL':
        ln([(0,-W/2),(0,W/2)])
        for x in (-3.,3.):ln([(x,-W/2),(x,W/2)])
        f.components.append((props.net(10.,net_height,net_height),(0,0,h),0))
    elif kind=='BADMINTON':
        for y in (-2.59,2.59):ln([(-L/2,y),(L/2,y)],.04)
        for x in (-1.98,1.98,-(L/2-.76),L/2-.76):ln([(x,-W/2),(x,W/2)],.04)
        for s in (-1,1):ln([(s*1.98,0),(s*L/2,0)],.04)
        f.components.append((props.net(6.7,1.55,1.524),(0,0,h),0))
    elif kind=='PICKLEBALL':
        for x in (-2.1336,2.1336):ln([(x,-W/2),(x,W/2)])
        for s in (-1,1):ln([(s*2.1336,0),(s*L/2,0)])
        f.components.append((props.net(6.7,.9144,.8636),(0,0,h),0))
    elif kind in ('FOOTBALL','FUTSAL'):
        R=9.15 if kind=='FOOTBALL' else 3.;circ(0,0,R)
        if kind=='FOOTBALL':
            # Alternating mowing bands are separate face colours, not stretched UVs.
            for i in range(10):
                if i%2:base.plane(rect(-L/2+(i+.5)*L/10,0,L/10,W),h+.0012,MAT['GrassDark'])
            for s in (-1,1):
                for depth,wide in ((16.5,40.32),(5.5,18.32)):
                    ln([(s*L/2,-wide/2),(s*(L/2-depth),-wide/2),(s*(L/2-depth),wide/2),(s*L/2,wide/2)],.10)
                spot=s*(L/2-11);circ(spot,0,.11)
                theta=math.acos(5.5/9.15)
                circ(spot,0,9.15,math.pi-theta if s==1 else -theta,math.pi+theta if s==1 else theta)
                f.components.append((props.goal(),(s*L/2,0,h),0 if s==1 else 180))
        else:
            for s in (-1,1):
                # Recreational futsal approximation, deliberately not certified.
                circ(s*L/2,0,6.,math.pi/2 if s==1 else -math.pi/2,3*math.pi/2 if s==1 else math.pi/2)
                circ(s*(L/2-6),0,.10)
                f.components.append((props.goal(3.,2.,1.5),(s*L/2,0,h),0 if s==1 else 180))
            f.notes.append('Futsal penalty layout is simplified for visual scenery.')
    elif kind=='FITNESS':
        f.components.append((props.fitness(),(0,0,h),0))
        for x in (-4,4):f.components.append((props.bench(),(x,-3,h),0))
    elif kind=='TABLE_TENNIS':f.components.append((props.table_tennis(),(0,0,h),0))
    if fencing and kind in ('BASKETBALL','TENNIS','FUTSAL','BADMINTON','PICKLEBALL'):
        f.components.append((props.fence(PL-.2,PW-.2,3. if kind!='BASKETBALL' else 2.6,gate_width),(0,0,h),0))
    return f

def stadium_boundary(straight,r,n=100):
    # CCW stadium: right semicircle, upper straight, left semicircle, lower straight.
    return arc(straight/2,0,r,-math.pi/2,math.pi/2,n//2)+arc(-straight/2,0,r,math.pi/2,3*math.pi/2,n//2)

def track(lap=400.,lanes=6,height=.18,detail='BALANCED'):
    if lanes not in (2,3,4,5,6,7,8):raise ValueError('Track lanes must be 2..8.')
    r=36.5 if lap>=350 else 16.
    straight=(lap-TAU*(r+.30))/2
    if straight<18.:raise ValueError('Lap length is too short for this radius.')
    width=1.22;outer=r+lanes*width
    mesh=Mesh(f'SM_PK01_Track_{lap:g}_{lanes}_{round(height*1000)}');h=height
    n=72 if detail=='DRAFT' else 128
    # Each lane is an annular ribbon partition, open center stays available for the pitch.
    for j in range(lanes):
        inner=stadium_boundary(straight,r+j*width,n);out=stadium_boundary(straight,r+(j+1)*width,n)
        mat=MAT['EPDM_Terracotta'] if j%2==0 else MAT['EPDM_Sage']
        for i in range(len(inner)):
            k=(i+1)%len(inner);poly=[inner[i],out[i],out[k],inner[k]]
            mesh.prism(poly,0.,h,mat,uvscale=.8)
    lines=Mesh(mesh.name+'_Lines');lines.surface_only=True
    for j in range(lanes+1):lines.line(stadium_boundary(straight,r+j*width,n),.05,h+.003,closed=True)
    # Shared finish reference; stagger starts and hurdle marks intentionally omitted.
    lines.line([(0,-outer),(0,-r)],.06,h+.004)
    for j in range(lanes):
        y=-r-(j+.5)*width
        # Discrete lane ticks, no font dependency.
        for k in range(j+1):lines.line([(-.30+k*.10,y-.23),(-.30+k*.10,y+.23)],.045,h+.005)
    mesh.meta.update(lap_length_m=2*straight+TAU*(r+.30),inner_radius_m=r,straight_m=straight,lane_width_m=width,lanes=lanes)
    mesh.meta['collision_note']='Track uses complex-as-simple static collision in UE; no solid box across infield.'
    return mesh,lines,(straight+2*outer,2*outer),mesh.meta
