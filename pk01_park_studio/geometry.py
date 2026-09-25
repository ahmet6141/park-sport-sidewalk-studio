"""Dependency-free geometry, closed solid primitives and open surface primitives.
Metres, right-handed Z-up; XY plane. This is scenery, NOT construction engineering.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math, random, hashlib, json
from .vendor import sw01_core as sw

TAU = math.tau
MATERIAL_NAMES = [s['name'] for s in sw.MATERIALS] + [
    'M_PK01_Grass', 'M_PK01_GrassDark', 'M_PK01_EPDM_Teal', 'M_PK01_EPDM_Terracotta',
    'M_PK01_EPDM_Sage', 'M_PK01_Line', 'M_PK01_Timber', 'M_PK01_Steel',
    'M_PK01_Bark', 'M_PK01_Leaf', 'M_PK01_Mulch', 'M_PK01_Stone',
    'M_PK01_Water', 'M_PK01_Glass', 'M_PK01_Emission', 'M_PK01_Flower',
    'M_PK01_Net', 'M_PK01_Gravel', 'M_PK01_Soil', 'M_PK01_CourtBlue',
]
MAT = {n.removeprefix('M_PK01_').removeprefix('M_SW01_'): i for i,n in enumerate(MATERIAL_NAMES)}

def vadd(a,b): return tuple(x+y for x,y in zip(a,b))
def vsub(a,b): return tuple(x-y for x,y in zip(a,b))
def vmul(a,s): return tuple(x*s for x in a)
def vdot(a,b): return sum(x*y for x,y in zip(a,b))
def vcross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def vlength(a): return math.sqrt(vdot(a,a))
def vunit(a):
    n=vlength(a)
    if n<1e-10: raise ValueError('Zero-length direction in primitive.')
    return vmul(a,1/n)
def transform(p,loc=(0,0,0),yaw=0,scale=(1,1,1)):
    a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
    x,y,z=(p[i]*scale[i] for i in range(3))
    return (loc[0]+c*x-s*y,loc[1]+s*x+c*y,loc[2]+z)

def rect(cx,cy,l,w): return [(cx-l/2,cy-w/2),(cx+l/2,cy-w/2),(cx+l/2,cy+w/2),(cx-l/2,cy+w/2)]
def ellipse(rx,ry,n=96,cx=0,cy=0,irregular=0):
    out=[]
    for i in range(n):
        a=TAU*i/n;f=1+irregular*(.65*math.sin(3*a+.4)+.35*math.sin(5*a-1.1))
        out.append((cx+rx*f*math.cos(a),cy+ry*f*math.sin(a)))
    return out

def arc(cx,cy,r,start,end,n=None):
    n=n or max(8,int(abs(end-start)*r/.22))
    return [(cx+r*math.cos(start+(end-start)*i/n),cy+r*math.sin(start+(end-start)*i/n)) for i in range(n+1)]

class Mesh(sw.MeshData):
    """SW01-compatible triangle buffer. Smooth shading is tracked explicitly."""
    def __init__(self,name):
        super().__init__(name)
        self.smooth=[]
        self._smooth=False
        self.collision=[]  # (minx,miny,minz,maxx,maxy,maxz) convex boxes only.
        self.surface_only=False
        self.meta={}
    def face(self,indices,uv,mat):
        super().face(indices,uv,mat)
        self.smooth.append(self._smooth)
    def box(self,center,size,mat,bevel=0,tint=(1,1,1),uvscale=1.):
        x,y,z=center;l,w,h=size
        if min(l,w,h)<=0:raise ValueError('Box dimensions must be positive.')
        self.prism(rect(x,y,l,w),z-h/2,z+h/2,mat,color=tint,bevel=min(bevel,h*.3,min(l,w)*.1),uvscale=uvscale)
    def add_collision_box(self,center,size):
        self.collision.append(tuple(center[i]-size[i]/2 for i in range(3))+tuple(center[i]+size[i]/2 for i in range(3)))
    def plane(self,poly,z,mat,uvscale=1,tint=(1,1,1)):
        p=sw.clean_polygon(poly)
        if len(p)<3:raise ValueError('Invalid surface polygon.')
        start=len(self.vertices)
        self.vertices.extend((x,y,z) for x,y in p);self.colors.extend([tint]*len(p))
        for a,b,c in sw.triangulate(p):
            self.face((start+a,start+b,start+c),tuple((p[i][0]/uvscale,p[i][1]/uvscale) for i in (a,b,c)),mat)
    def cylinder(self,a,b,r,mat,r2=None,n=10,tint=(1,1,1),caps=True):
        a,b=tuple(a),tuple(b);r2=r if r2 is None else r2
        if min(r,r2)<=0:raise ValueError('Cylinder radii must be positive.')
        d=vunit(vsub(b,a));ref=(0,0,1) if abs(d[2])<.94 else (0,1,0)
        u=vunit(vcross(ref,d));v=vcross(d,u);start=len(self.vertices);L=vlength(vsub(b,a))
        for center,rad in ((a,r),(b,r2)):
            for i in range(n):
                t=TAU*i/n;off=vadd(vmul(u,rad*math.cos(t)),vmul(v,rad*math.sin(t)))
                self.vertices.append(vadd(center,off));self.colors.append(tint)
        self._smooth=True
        for i in range(n):
            j=(i+1)%n;u0=i/n;u1=(i+1)/n
            self.face((start+i,start+j,start+n+j),((u0,0),(u1,0),(u1,L)),mat)
            self.face((start+i,start+n+j,start+n+i),((u0,0),(u1,L),(u0,L)),mat)
        self._smooth=False
        if caps:
            for i in range(1,n-1):
                self.face((start,start+i+1,start+i),((.5,.5),(1,1),(1,0)),mat)
                self.face((start+n,start+n+i,start+n+i+1),((.5,.5),(1,0),(1,1)),mat)
        self.solids.append((start,2*n,'cylinder'))
    def line(self,points,width,z,mat=MAT['Line'],closed=False):
        """Flat marking ribbon. Open boundary by design; never receives a collider."""
        pts=list(points)
        if closed and pts[-1]!=pts[0]:pts.append(pts[0])
        for a,b in zip(pts,pts[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dy)
            if L<1e-8:continue
            nx,ny=-dy/L*width/2,dx/L*width/2
            self.plane([(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),(b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)],z,mat)
    def tube(self,points,r,mat,n=6,tint=(1,1,1)):
        for a,b in zip(points,points[1:]):
            if vlength(vsub(b,a))>1e-7:self.cylinder(a,b,r,mat,n=n,tint=tint)
    def leaf(self,p,axis,length,width,roll,mat=MAT['Leaf'],tint=(1,1,1)):
        d=vunit(axis);ref=(0,0,1) if abs(d[2])<.95 else (1,0,0)
        u=vunit(vcross(ref,d));v=vcross(d,u)
        u=vadd(vmul(u,math.cos(roll)),vmul(v,math.sin(roll)));normal=vunit(vcross(d,u))
        q=[p,vadd(p,vadd(vmul(d,length*.45),vmul(u,width*.5))),vadd(p,vmul(d,length)),
           vadd(p,vadd(vmul(d,length*.45),vmul(u,-width*.5))),
           vadd(p,vadd(vmul(d,length*.44),vmul(normal,width*.15)))]
        start=len(self.vertices);self.vertices.extend(q);self.colors.extend([tint]*5)
        uv=[(.5,0),(0,.45),(.5,1),(1,.45),(.5,.44)]
        self._smooth=True
        for a,b,c in ((0,1,4),(1,2,4),(2,3,4),(3,0,4)):
            self.face((start+a,start+b,start+c),(uv[a],uv[b],uv[c]),mat)
        self._smooth=False
        self.surface_only=True
    def append(self,other,location=(0,0,0),yaw=0,scale=(1,1,1)):
        off=len(self.vertices);self.vertices.extend(transform(p,location,yaw,scale) for p in other.vertices)
        self.colors.extend(other.colors)
        self.triangles.extend(tuple(i+off for i in t) for t in other.triangles)
        self.uv.extend(other.uv);self.material_ids.extend(other.material_ids)
        self.smooth.extend(getattr(other,'smooth',[False]*len(other.triangles)))
    def bounds(self):
        if not self.vertices:return ((0,0,0),(0,0,0))
        return tuple(tuple(fn(p[i] for p in self.vertices) for i in range(3)) for fn in (min,max))
    def geometry_hash(self):
        data=[self.name,self.vertices,self.triangles,self.material_ids,self.colors,self.uv,self.smooth]
        return hashlib.sha256(json.dumps(data,separators=(',',':')).encode()).hexdigest()

def from_sw01(mesh,meta):
    result=Mesh(mesh.name)
    for k in ('vertices','triangles','uv','colors','material_ids','solids','warnings'):
        setattr(result,k,getattr(mesh,k))
    result.smooth=[False]*len(result.triangles)
    result.meta={'sw01':meta}
    return result

@dataclass
class Placement:
    asset: str
    location: tuple = (0.,0.,0.)
    yaw: float = 0.
    scale: tuple = (1.,1.,1.)
    zone: str = 'Root'
    category: str = 'Architecture'

@dataclass
class Zone:
    name: str
    location: tuple = (0.,0.,0.)
    yaw: float = 0.
    category: str = 'Architecture'
    settings: dict = field(default_factory=dict)

@dataclass
class Port:
    name: str
    location: tuple
    yaw: float
    width: float
    surface_height: float
    zone: str = 'Root'

@dataclass
class ScenePlan:
    name: str
    assets: dict = field(default_factory=dict)
    placements: list = field(default_factory=list)
    zones: dict = field(default_factory=dict)
    ports: list = field(default_factory=list)
    paths: list = field(default_factory=list)
    reservations: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    def asset(self,mesh):
        if mesh.name not in self.assets:self.assets[mesh.name]=mesh
        return mesh.name
    def place(self,mesh,location=(0,0,0),yaw=0,scale=(1,1,1),zone='Root',category='Architecture'):
        key=mesh if isinstance(mesh,str) else self.asset(mesh)
        if key not in self.assets:raise KeyError(key)
        p=Placement(key,tuple(location),yaw,tuple(scale),zone,category);self.placements.append(p);return p
    def zone(self,name,location=(0,0,0),yaw=0,category='Architecture',**settings):
        self.zones[name]=Zone(name,tuple(location),yaw,category,settings);return name
    def world_point(self,placement,p=(0,0,0)):
        q=transform(p,placement.location,placement.yaw,placement.scale)
        zone=self.zones.get(placement.zone)
        return transform(q,zone.location,zone.yaw) if zone else q
    def stats(self):
        unique=sum(len(m.triangles) for m in self.assets.values())
        evaluated=sum(len(self.assets[p.asset].triangles) for p in self.placements)
        return dict(assets=len(self.assets),placements=len(self.placements),zones=len(self.zones),ports=len(self.ports),unique_triangles=unique,instanced_triangles=evaluated)
