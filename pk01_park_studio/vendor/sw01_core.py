"""SW01 Sidewalk Studio -- deterministic, dependency-free mesh kernel.
Units: metres. X forward, Y left, Z up. Visual scenery, not civil certification.
Copyright 2026. Generated source: MIT. Generated meshes/textures: CC0.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict, replace
import bisect, math, random
from typing import Callable

EPS = 1e-9
V2 = tuple[float, float]
V3 = tuple[float, float, float]

def add(a, b): return (a[0] + b[0], a[1] + b[1])
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def mul(a, k): return (a[0] * k, a[1] * k)
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def length(a): return math.hypot(*a)
def unit(a):
    n = length(a)
    if n < EPS: raise ValueError('Zero-length path edge.')
    return mul(a, 1.0/n)
def lerp(a, b, t): return add(a, mul(sub(b, a), t))
def area(poly):
    return .5 * sum(cross(poly[i], poly[(i+1) % len(poly)]) for i in range(len(poly)))

def clean_polygon(poly, tolerance=1e-8):
    out = []
    for p in poly:
        p = (float(p[0]), float(p[1]))
        if not out or length(sub(p, out[-1])) > tolerance: out.append(p)
    if len(out) > 1 and length(sub(out[0], out[-1])) <= tolerance: out.pop()
    changed = True
    while changed and len(out) >= 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i-1], out[i], out[(i+1) % len(out)]
            if abs(cross(sub(b,a), sub(c,b))) < tolerance * max(length(sub(c,a)), .01) and dot(sub(b,a),sub(c,b)) >= -tolerance:
                out.pop(i); changed = True; break
    if len(out) < 3 or abs(area(out)) < 1e-10: return []
    if area(out) < 0: out.reverse()
    return out

def point_in_triangle(p,a,b,c,tol=1e-10):
    return (cross(sub(b,a),sub(p,a)) >= -tol and
            cross(sub(c,b),sub(p,b)) >= -tol and
            cross(sub(a,c),sub(p,c)) >= -tol)

def triangulate(poly):
    """Ear clipping on a simple, CCW polygon; never falls back to an unsafe fan."""
    n = len(poly)
    if n < 3: return []
    ids = list(range(n)); result=[]
    while len(ids)>3:
        found = False
        for k,b in enumerate(ids):
            a,c = ids[k-1],ids[(k+1)%len(ids)]
            if cross(sub(poly[b],poly[a]),sub(poly[c],poly[b])) <= 1e-12: continue
            if any(point_in_triangle(poly[i],poly[a],poly[b],poly[c])
                   for i in ids if i not in (a,b,c)): continue
            result.append((a,b,c));ids.pop(k);found=True;break
        if not found: raise ValueError('Non-simple or numerically degenerate polygon. Increase radius / reduce bevel.')
    if cross(sub(poly[ids[1]],poly[ids[0]]),sub(poly[ids[2]],poly[ids[0]]))>1e-12:
        result.append(tuple(ids))
    return result

def clip_convex(subject, clipper):
    """Sutherland-Hodgman. Convex clipper; connected intersection required.
    The intersection is validated by the mesher. This is NOT a polygon-union engine.
    """
    output = list(subject)
    if area(clipper)<0: clipper=list(reversed(clipper))
    for a,b in zip(clipper,clipper[1:]+clipper[:1]):
        e=sub(b,a); inp=output; output=[]
        if not inp: break
        s=inp[-1]; ds=cross(e,sub(s,a))
        for p in inp:
            dp=cross(e,sub(p,a))
            if (dp >= -EPS) != (ds >= -EPS):
                den=ds-dp
                if abs(den)>EPS: output.append(lerp(s,p,ds/den))
            if dp>=-EPS: output.append(p)
            s=p;ds=dp
    return clean_polygon(output)

def proper_intersect(a,b,c,d):
    ab,cd=sub(b,a),sub(d,c)
    den=cross(ab,cd)
    if abs(den)<EPS: return False
    t=cross(sub(c,a),cd)/den;u=cross(sub(c,a),ab)/den
    return EPS<t<1-EPS and EPS<u<1-EPS

def simple_polygon(p):
    n=len(p)
    for i in range(n):
        a,b=p[i],p[(i+1)%n];e=sub(b,a)
        for j in range(i+2,n):
            if i==0 and j==n-1: continue
            c,d=p[j],p[(j+1)%n]
            if proper_intersect(a,b,c,d): return False
            # Non-adjacent touching/overlapping edges form a weakly simple bridge,
            # usually a disconnected polygon/rectangle intersection.
            for q in (c,d):
                if abs(cross(e,sub(q,a)))<1e-10 and -1e-10<=dot(sub(q,a),e)<=dot(e,e)+1e-10:
                    return False
            f=sub(d,c)
            for q in (a,b):
                if abs(cross(f,sub(q,c)))<1e-10 and -1e-10<=dot(sub(q,c),f)<=dot(f,f)+1e-10:
                    return False
    return True


def merge_partition(polygons):
    """Remove shared directed edges of a planar triangle partition."""
    def key(p): return (round(p[0],9),round(p[1],9))
    edges={}
    for poly in polygons:
        for a,b in zip(poly,poly[1:]+poly[:1]):
            a,b=key(a),key(b)
            if a==b:continue
            if (b,a) in edges: del edges[(b,a)]
            else: edges[(a,b)]=True
    result=[]
    while edges:
        a,b=next(iter(edges));start=a;chain=[a];del edges[(a,b)]
        prev,current=a,b
        guard=0
        while current!=start:
            chain.append(current);opts=[v for u,v in edges if u==current]
            if not opts:raise ValueError('Cannot reconstruct a clipped paver boundary.')
            if len(opts)>1:
                inc=sub(current,prev)
                # Most clockwise outgoing edge keeps a point-touching shell separate.
                opts.sort(key=lambda q: math.atan2(cross(inc,sub(q,current)),dot(inc,sub(q,current))))
            nxt=opts[0];del edges[(current,nxt)];prev,current=current,nxt;guard+=1
            if guard>10000:raise ValueError('Boundary reconstruction exceeded safety limit.')
        q=clean_polygon(chain)
        if q:result.append(q)
    return result


def clip_regions(subject,clipper,subject_triangles=None):
    p=clip_convex(subject,clipper)
    if not p:return []
    if simple_polygon(p):return [p]
    ts=subject_triangles if subject_triangles is not None else triangulate(subject)
    parts=[]
    for tri in ts:
        q=clip_convex([subject[i] for i in tri],clipper)
        if q:parts.append(q)
    return merge_partition(parts)

def inset_polygon(poly, distance):
    if distance<=0: return list(poly)
    out=[]
    for i,p in enumerate(poly):
        u,v=unit(sub(p,poly[i-1])),unit(sub(poly[(i+1)%len(poly)],p))
        n1,n2=(-u[1],u[0]),(-v[1],v[0]);den=1+dot(n1,n2)
        if den<.025: return None
        d=mul(add(n1,n2), distance/den)
        if length(d)>distance*8: return None
        out.append(add(p,d))
    if area(out)<=1e-8 or area(out)>=area(poly) or not simple_polygon(out): return None
    return out

@dataclass
class Config:
    width: float = 2.40
    height: float = .18
    base_depth: float = .07
    paver_thickness: float = .06
    paver_length: float = .40
    paver_width: float = .20
    joint: float = .006
    bevel: float = .003
    pattern: str = 'HERRINGBONE'  # HERRINGBONE / RUNNING / STACK / BASKET / SLABS
    pattern_angle: float = 45.
    curb_width: float = .18
    curb_length: float = .80
    curb_bevel: float = .008
    curb_left: bool = True
    curb_right: bool = True
    border_width: float = .12
    tactile: bool = False
    tactile_offset: float = 0.
    tactile_width: float = .30
    tactile_pitch: float = .40
    tactile_relief: float = .004
    tactile_mode: str = 'RIBS'  # RIBS or DOMES (visual only)
    drainage: bool = False
    drain_width: float = .12
    drain_interval: float = 3.2
    paver_tint: tuple = (.94,.96,.96)
    curb_tint: tuple = (1.,1.,1.)
    border_tint: tuple = (.32,.35,.39)
    variation: float = .075
    texture_metres: float = 1.
    seed: int = 41
    end_elevation: float = 0.
    max_pavers: int = 18000
    min_cut_area: float = .00003
    curve_step: float = .18

    def validate(self):
        numbers=[self.width,self.height,self.joint,self.bevel,self.curb_width,self.curb_length,
                 self.paver_length,self.paver_width,self.texture_metres,self.curve_step,
                 self.end_elevation,self.variation,self.pattern_angle,self.base_depth,self.paver_thickness,
                 self.curb_bevel,self.border_width,self.tactile_offset,self.tactile_width,self.tactile_pitch,
                 self.tactile_relief,self.drain_width,self.drain_interval,self.min_cut_area]
        if not all(math.isfinite(float(v)) for v in numbers): raise ValueError('All dimensions must be finite.')
        if not 0.6<=self.width<=12: raise ValueError('width must be 0.6..12 m.')
        if not .06<=self.height<=.50: raise ValueError('height must be 0.06..0.50 m.')
        if not .001<=self.joint<=.025: raise ValueError('joint must be 1..25 mm.')
        if not .10<=self.paver_length<=2 or not .08<=self.paver_width<=1.2: raise ValueError('Paver dimensions out of range.')
        if not .025<=self.paver_thickness<=self.height: raise ValueError('Paver thickness must fit the height.')
        if not 0<=self.bevel<=min(.015,self.paver_thickness*.3): raise ValueError('Invalid bevel.')
        if not .06<=self.curb_width<=.40 or not .15<=self.curb_length<=2.: raise ValueError('Invalid curb size.')
        if not 0<=self.border_width<=.40 or not 0<=self.variation<=.25: raise ValueError('Invalid border / colour variation.')
        if not .15<=self.texture_metres<=10 or not .04<=self.curve_step<=.60: raise ValueError('Invalid texture / curve sampling scale.')
        if not .01<=self.base_depth<=1 or not 0<=self.curb_bevel<=.02: raise ValueError('Invalid base depth / curb bevel.')
        if not .20<=self.tactile_width<=.8 or not .12<=self.tactile_pitch<=1.: raise ValueError('Invalid tactile tile dimensions.')
        if not .002<=self.tactile_relief<=.008: raise ValueError('Invalid tactile relief.')
        if not .04<=self.drain_width<=.30 or not .8<=self.drain_interval<=20: raise ValueError('Invalid drain dimensions / interval.')
        if not 0<=self.min_cut_area<=.005 or abs(self.end_elevation)>5.: raise ValueError('Invalid cut threshold / elevation.')
        for tint in (self.paver_tint,self.curb_tint,self.border_tint):
            if len(tint)!=3 or not all(math.isfinite(x) and 0<=x<=1 for x in tint): raise ValueError('Colours must be finite RGB values in 0..1.')
        if self.pattern not in ('HERRINGBONE','RUNNING','STACK','BASKET','SLABS'): raise ValueError('Unknown pattern.')
        if self.tactile_mode not in ('RIBS','DOMES'): raise ValueError('Unknown tactile mode.')
        if self.max_pavers<1 or self.max_pavers>100000: raise ValueError('Invalid safety limit.')
        inner=self.width-self.curb_width*(int(self.curb_left)+int(self.curb_right))-2*self.border_width
        if inner<.40: raise ValueError('Width is too small for curbs and borders.')
        pright=-self.width/2+(self.curb_width if self.curb_right else 0)+self.border_width
        pleft=self.width/2-(self.curb_width if self.curb_left else 0)-self.border_width
        if self.tactile and (self.tactile_offset-self.tactile_width/2<pright+.05 or self.tactile_offset+self.tactile_width/2>pleft-.05):
            raise ValueError('Tactile strip would run into the border. Increase width / reduce offset.')

@dataclass
class MeshData:
    name: str
    vertices: list = field(default_factory=list)
    triangles: list = field(default_factory=list)
    uv: list = field(default_factory=list)      # 3 UV pairs for every triangle
    material_ids: list = field(default_factory=list)
    colors: list = field(default_factory=list)  # linear vertex RGB, one per vertex
    solids: list = field(default_factory=list)  # (first_vertex, count, label)
    warnings: list = field(default_factory=list)

    def face(self,ids,uv,mat):
        self.triangles.append(tuple(ids)); self.uv.append(tuple(uv)); self.material_ids.append(mat)

    def prism(self, polygon, z0, z1, mat, color=(1.,1.,1.), bevel=0., uvscale=1., uvshift=(0.,0.), label='', elevation=None):
        p=clean_polygon(polygon)
        if not p: return False
        if not simple_polygon(p): raise ValueError(f'Invalid polygon in {label}')
        # Extremely thin perimeter cuts remain flat, rather than receiving a destructive bevel.
        inner=inset_polygon(p,bevel) if bevel>0 else None
        if inner is None: bevel=0
        n=len(p);start=len(self.vertices)
        loops=[(p,z0),(p,z1-bevel)]+([(inner,z1)] if bevel else [])
        for ring,z in loops:
            for x,y in ring:
                self.vertices.append((x,y,z+(elevation((x,y)) if elevation else 0.)))
                self.colors.append(tuple(color))
        def topuv(q): return (q[0]/uvscale+uvshift[0], q[1]/uvscale+uvshift[1])
        for a,b,c in triangulate(p):
            self.face((start+c,start+b,start+a),(topuv(p[c]),topuv(p[b]),topuv(p[a])),mat)
        topstart=start+(len(loops)-1)*n;tp=loops[-1][0]
        for a,b,c in triangulate(tp):
            self.face((topstart+a,topstart+b,topstart+c),(topuv(tp[a]),topuv(tp[b]),topuv(tp[c])),mat)
        for k in range(len(loops)-1):
            distance=0.
            lo,zlo=loops[k];hi,zhi=loops[k+1]
            for i in range(n):
                j=(i+1)%n;l=length(sub(lo[j],lo[i]));a=start+k*n+i;b=start+k*n+j;c=b+n;d=a+n
                if k==0:
                    uv=[(distance/uvscale,zlo/uvscale),((distance+l)/uvscale,zlo/uvscale),
                        ((distance+l)/uvscale,zhi/uvscale),(distance/uvscale,zhi/uvscale)]
                else: uv=[topuv(lo[i]),topuv(lo[j]),topuv(hi[j]),topuv(hi[i])]
                self.face((a,b,c),(uv[0],uv[1],uv[2]),mat);self.face((a,c,d),(uv[0],uv[2],uv[3]),mat)
                distance+=l
        self.solids.append((start,len(self.vertices)-start,label))
        return True

# Material slots are stable across all modules and both applications.
MATERIALS = [
    {'name':'M_SW01_Mortar','texture':'Mortar','color':(.22,.215,.20),'roughness':.9,'metallic':0.},
    {'name':'M_SW01_Pavers','texture':'PaverConcrete','color':(.48,.49,.49),'roughness':.76,'metallic':0.},
    {'name':'M_SW01_Curb','texture':'CurbConcrete','color':(.53,.52,.49),'roughness':.82,'metallic':0.},
    {'name':'M_SW01_Border','texture':'PaverConcrete','color':(.48,.49,.49),'roughness':.76,'metallic':0.},
    {'name':'M_SW01_Tactile','texture':'Tactile','color':(.60,.34,.065),'roughness':.72,'metallic':0.},
    {'name':'M_SW01_Metal','texture':'Metal','color':(.085,.095,.10),'roughness':.47,'metallic':1.},
]

class Path:
    def __init__(self,points):
        self.points=[]
        for p in points:
            p=tuple(map(float,p[:2]))
            if not all(math.isfinite(x) for x in p): raise ValueError('Non-finite path.')
            if not self.points or length(sub(p,self.points[-1]))>1e-5: self.points.append(p)
        if len(self.points)<2: raise ValueError('At least two distinct path points required.')
        if len(self.points)>1500: raise ValueError('Path has more than 1500 samples. Increase sample step.')
        self.dist=[0.]
        self.tangents=[]
        for a,b in zip(self.points,self.points[1:]):
            self.dist.append(self.dist[-1]+length(sub(b,a)));self.tangents.append(unit(sub(b,a)))
        if self.dist[-1]>300: raise ValueError('Split paths longer than 300 m into smaller assets.')
        self.normals=[]
        for i in range(len(self.points)):
            t1=self.tangents[max(0,i-1)];t2=self.tangents[min(i,len(self.tangents)-1)]
            n1,n2=(-t1[1],t1[0]),(-t2[1],t2[0]);den=1+dot(n1,n2)
            if den<.29: raise ValueError('Turn is too sharp. Use a fillet or a junction asset; maximum hard turn ~135 degrees.')
            self.normals.append(mul(add(n1,n2),1/den))
        self.length=self.dist[-1]

    def sample(self,s,offset=0.):
        s=max(0.,min(self.length,s));i=min(bisect.bisect_right(self.dist,s)-1,len(self.points)-2)
        t=(s-self.dist[i])/(self.dist[i+1]-self.dist[i]);p=lerp(self.points[i],self.points[i+1],t)
        return add(p,mul(lerp(self.normals[i],self.normals[i+1],t),offset))

    def range_samples(self,a,b,offset):
        return [self.sample(a,offset)]+[add(p,mul(n,offset)) for s,p,n in zip(self.dist,self.points,self.normals) if a+EPS<s<b-EPS]+[self.sample(b,offset)]

    def strip(self,a,b,right,left):
        return clean_polygon(self.range_samples(a,b,right)+list(reversed(self.range_samples(a,b,left))))

    def projection(self,p):
        best=(float('inf'),0.)
        for i,(a,b) in enumerate(zip(self.points,self.points[1:])):
            e=sub(b,a);t=max(0.,min(1.,dot(sub(p,a),e)/dot(e,e)));q=lerp(a,b,t)
            d=dot(sub(p,q),sub(p,q))
            if d<best[0]: best=(d,self.dist[i]+t*(self.dist[i+1]-self.dist[i]))
        return best[1]


def make_path(kind='STRAIGHT',length_m=4.,radius=4.,angle=90.,leg=3.,step=.18,points=None):
    kind=kind.upper()
    if kind=='CUSTOM': return Path(points)
    if kind in ('STRAIGHT','RAMP'):
        if length_m<.4: raise ValueError('Straight length must be at least 0.4 m.')
        return Path([(0.,0.),(float(length_m),0.)])
    if kind=='ARC':
        if not .01<abs(angle)<=150 or radius<=0: raise ValueError('Arc angle must be nonzero and <=150 degrees; radius positive.')
        a=math.radians(abs(angle));sgn=1 if angle>0 else -1;n=max(8,int(math.ceil(radius*a/step)))
        pts=[(radius*math.sin(a*i/n),sgn*radius*(1-math.cos(a*i/n))) for i in range(n+1)]
        path=Path(pts)
        # Exact radial normals at the ends keep neighbouring modules flush.
        path.normals[0]=(0.,1.);path.normals[-1]=(-sgn*math.sin(a),math.cos(a))
        return path
    if kind=='CORNER':
        if not 1<=abs(angle)<=135: raise ValueError('Corner angle must be 1..135 degrees.')
        a=math.radians(angle)
        return Path([(0.,0.),(leg,0.),(leg+leg*math.cos(a),leg*math.sin(a))])
    if kind=='S_CURVE':
        a=math.radians(abs(angle));sgn=1 if angle>0 else -1
        n=max(10,int(math.ceil(radius*a/step)))
        first=[(radius*math.sin(a*i/n),sgn*radius*(1-math.cos(a*i/n))) for i in range(n+1)]
        end=first[-1];theta=sgn*a
        second=[]
        for i in range(1,n+1):
            u=a*i/n;x=radius*math.sin(u);y=-sgn*radius*(1-math.cos(u))
            second.append((end[0]+math.cos(theta)*x-math.sin(theta)*y,end[1]+math.sin(theta)*x+math.cos(theta)*y))
        path=Path(first+second);path.normals[0]=(0.,1.);path.normals[-1]=(0.,1.)
        return path
    raise ValueError('Unknown path type '+kind)


def tile_rectangles(bounds,cfg):
    xmin,ymin,xmax,ymax=bounds
    theta=math.radians(cfg.pattern_angle);ct,st=math.cos(theta),math.sin(theta)
    def rot(p): return (ct*p[0]-st*p[1],st*p[0]+ct*p[1])
    def unrot(p): return (ct*p[0]+st*p[1],-st*p[0]+ct*p[1])
    bb=[unrot(p) for p in [(xmin,ymin),(xmin,ymax),(xmax,ymin),(xmax,ymax)]]
    ax=min(x for x,y in bb);bx=max(x for x,y in bb);ay=min(y for x,y in bb);by=max(y for x,y in bb)
    gap=cfg.joint
    def rect(x,y,w,h):
        return [rot((x+gap/2,y+gap/2)),rot((x+w-gap/2,y+gap/2)),
                rot((x+w-gap/2,y+h-gap/2)),rot((x+gap/2,y+h-gap/2))]
    w=cfg.paver_width;l=cfg.paver_length
    if cfg.pattern in ('STACK','RUNNING','SLABS'):
        if cfg.pattern=='SLABS': l=max(.60,l);w=max(.40,w)
        for j in range(math.floor(ay/w)-2,math.ceil(by/w)+2):
            off=(l/2 if j%2 else 0) if cfg.pattern=='RUNNING' else 0
            for i in range(math.floor((ax-off)/l)-2,math.ceil((bx-off)/l)+2):
                yield rect(i*l+off,j*w,l,w)
    elif cfg.pattern=='HERRINGBONE':
        for j in range(math.floor(ay/w)-3,math.ceil(by/w)+3):
            for i in range(math.floor(ax/w)-3,math.ceil(bx/w)+3):
                residue=(i-j)%4
                if residue==0: yield rect(i*w,j*w,2*w,w)
                elif residue==3: yield rect(i*w,j*w,w,2*w)
    elif cfg.pattern=='BASKET':
        for j in range(math.floor(ay/(2*w))-2,math.ceil(by/(2*w))+2):
            for i in range(math.floor(ax/(2*w))-2,math.ceil(bx/(2*w))+2):
                for k in range(2):
                    if (i+j)%2: yield rect(2*i*w+k*w,2*j*w,w,2*w)
                    else: yield rect(2*i*w,2*j*w+k*w,2*w,w)


def build_module(name,path,cfg):
    cfg.validate();mesh=MeshData(name);rng=random.Random(cfg.seed)
    half=cfg.width/2;left=half-(cfg.curb_width if cfg.curb_left else 0.)
    right=-half+(cfg.curb_width if cfg.curb_right else 0.)
    fp=path.strip(0,path.length,-half,half)
    if not simple_polygon(fp): raise ValueError('Offset footprint intersects itself. Widen turn radius, reduce width, or split the path.')
    for n in path.normals:
        if length(n)>2.65: raise ValueError('Miter ratio too large.')
    elev=(lambda p:cfg.end_elevation*path.projection(p)/path.length) if cfg.end_elevation else None
    def prism(p,z0,z1,mat,tint=(1.,1.,1.),bevel=0,label=''):
        var=rng.uniform(1-cfg.variation,1+cfg.variation) if mat in (1,2,3) else 1.
        return mesh.prism(p,z0,z1,mat,tuple(min(1.,max(.04,v*var)) for v in tint),bevel,cfg.texture_metres,
                          (rng.uniform(0,7),rng.uniform(0,7)),label,elev)
    # Mortar bed stops under the pavers: there is no coplanar face at the walking surface.
    prism(path.strip(0,path.length,right,left),-cfg.base_depth,cfg.height-cfg.paver_thickness-.004,0,label='bed')
    breaks=[0.]+[s for i,s in enumerate(path.dist[1:-1],1)
                    if dot(path.tangents[i-1],path.tangents[i])<math.cos(math.radians(10))]+[path.length]
    def courses(a,b,mat,pitch,tint,z0,z1,bevel,label):
        for s0,s1 in zip(breaks,breaks[1:]):
            num=max(1,int(math.ceil((s1-s0)/pitch)))
            for j in range(num):
                start=s0+(s1-s0)*j/num+cfg.joint/2
                end=s0+(s1-s0)*(j+1)/num-cfg.joint/2
                if end<=start:continue
                prism(path.strip(start,end,a,b),z0,z1,mat,tint,bevel,label)
    if cfg.curb_right: courses(-half,right,2,cfg.curb_length,cfg.curb_tint,-cfg.base_depth,cfg.height,cfg.curb_bevel,'curb_R')
    if cfg.curb_left: courses(left,half,2,cfg.curb_length,cfg.curb_tint,-cfg.base_depth,cfg.height,cfg.curb_bevel,'curb_L')
    pright,pleft=right+cfg.border_width,left-cfg.border_width
    if cfg.border_width>0:
        courses(right,pright,3,.40,cfg.border_tint,cfg.height-cfg.paver_thickness,cfg.height,cfg.bevel,'border_R')
        courses(pleft,left,3,.40,cfg.border_tint,cfg.height-cfg.paver_thickness,cfg.height,cfg.bevel,'border_L')
    # Split the paver domain, rather than laying a tactile mesh over existing pavers.
    bands=[(pright,pleft)]
    if cfg.tactile:
        tr=cfg.tactile_offset-cfg.tactile_width/2;tl=cfg.tactile_offset+cfg.tactile_width/2
        bands=[(pright,tr-cfg.joint/2),(tl+cfg.joint/2,pleft)]
        courses(tr,tl,4,cfg.tactile_pitch,(1.,1.,1.),cfg.height-cfg.paver_thickness,cfg.height,.002,'tactile_tile')
        if cfg.tactile_mode=='RIBS':
            ribw=.019
            for s0,s1 in zip(breaks,breaks[1:]):
                num=max(1,math.ceil((s1-s0)/cfg.tactile_pitch))
                for j in range(num):
                    a=s0+(s1-s0)*j/num+.04;b=s0+(s1-s0)*(j+1)/num-.04
                    for k in range(4):
                        off=tr+.055+k*(cfg.tactile_width-.11)/3
                        if b>a:prism(path.strip(a,b,off-ribw/2,off+ribw/2),cfg.height,cfg.height+cfg.tactile_relief,4,bevel=.0015,label='tactile_rib')
        else:
            n=max(1,int(path.length/.065))
            for i in range(n):
                s=(i+.5)*path.length/n
                for k in range(max(1,int(cfg.tactile_width/.06))):
                    off=tr+.035+.06*k
                    if off>tl-.02: continue
                    x,y=path.sample(s,off)
                    circle=[(x+.0125*math.cos(t*math.tau/12),y+.0125*math.sin(t*math.tau/12)) for t in range(12)]
                    prism(circle,cfg.height,cfg.height+cfg.tactile_relief,4,bevel=.002,label='tactile_dome')
    pavement_polygons=[path.strip(cfg.joint/2,path.length-cfg.joint/2,a+cfg.joint/2,b-cfg.joint/2)
                       for a,b in bands if b-a>cfg.joint]
    drains=[]
    # Grate recesses are reserved in the paver field (not z-fighting overlays).
    if cfg.drainage:
        if len(path.points)>2: mesh.warnings.append('Drain grates are only generated on STRAIGHT/RAMP paths; curve drainage skipped.')
        else:
            for k in range(1,max(2,int(path.length/cfg.drain_interval)+1)):
                x=min(path.length-.45,k*cfg.drain_interval)
                if x<.4:continue
                drain=[(x-.30,pright+.06),(x+.30,pright+.06),(x+.30,pright+.06+cfg.drain_width),(x-.30,pright+.06+cfg.drain_width)]
                drains.append(drain)
    def subtract_rect(poly,rect):
        """Convex rect subtraction expressed as 4 non-overlapping halfplane regions."""
        x0,y0=rect[0];x1,y1=rect[2];B=1e5
        cutters=[[( -B,-B),(x0,-B),(x0,B),(-B,B)],[(x1,-B),(B,-B),(B,B),(x1,B)],
                 [(x0,-B),(x1,-B),(x1,y0),(x0,y0)],[(x0,y1),(x1,y1),(x1,B),(x0,B)]]
        return [q for c in cutters if (q:=clip_convex(poly,c))]
    count=0;cut_area=0.
    for domain in pavement_polygons:
        domain_triangles=triangulate(domain)
        bounds=(min(x for x,y in domain),min(y for x,y in domain),max(x for x,y in domain),max(y for x,y in domain))
        for rect in tile_rectangles(bounds,cfg):
            pieces=clip_regions(domain,rect,domain_triangles)
            if not pieces:continue
            p=[v for piece in pieces for v in piece]
            for d in drains:
                if max(x for x,y in p)<d[0][0] or min(x for x,y in p)>d[2][0] or max(y for x,y in p)<d[0][1] or min(y for x,y in p)>d[2][1]:continue
                pieces=[subp for p0 in pieces for subp in subtract_rect(p0,d)]
            for p0 in pieces:
                if area(p0)<cfg.min_cut_area:cut_area+=area(p0);continue
                count+=1
                if count>cfg.max_pavers:raise ValueError(f'Safety limit of {cfg.max_pavers} pavers exceeded. Split path into modules.')
                prism(p0,cfg.height-cfg.paver_thickness,cfg.height,1,cfg.paver_tint,cfg.bevel,'paver')
    for d in drains:
        x0,y0=d[0];x1,y1=d[2]
        def box(xa,ya,xb,yb,z0,z1,label):prism([(xa,ya),(xb,ya),(xb,yb),(xa,yb)],z0,z1,5,bevel=.001,label=label)
        box(x0,y0,x1,y1,cfg.height-.035,cfg.height-.025,'grate_tray')
        box(x0,y0,x1,y0+.01,cfg.height-.025,cfg.height,'grate_frame')
        box(x0,y1-.01,x1,y1,cfg.height-.025,cfg.height,'grate_frame')
        for k in range(21):
            x=x0+.012+k*(x1-x0-.03)/20
            box(x,y0+.01,x+.008,y1-.01,cfg.height-.018,cfg.height,'grate_bar')
    if cut_area>0:mesh.warnings.append(f'{cut_area:.6f} m² of sub-threshold edge slivers omitted (<{cfg.min_cut_area} m² each).')
    # Simple collision is a chain of convex trapezoidal prisms; no single concave UCX hull.
    collision=[]
    for i in range(len(path.points)-1):
        a,b=path.dist[i:i+2]
        collision.append({'polygon':path.strip(a,b,-half,half),'z0':-cfg.base_depth,'z1':cfg.height,
                          'end_elevation':cfg.end_elevation})
    t0=path.tangents[0];t1=path.tangents[-1]
    # Derive exact tangent from end normals; arc end tangents are not chord approximations.
    n0=unit(path.normals[0]);n1=unit(path.normals[-1]);t0=(n0[1],-n0[0]);t1=(n1[1],-n1[0])
    metadata={'name':name,'config':asdict(cfg),'length_m':path.length,'pavers':count,
              'vertices':len(mesh.vertices),'triangles':len(mesh.triangles),'solids':len(mesh.solids),
              'path':path.points,'warnings':mesh.warnings,
              'in':{'location':[path.points[0][0],path.points[0][1],0.], 'yaw_degrees':math.degrees(math.atan2(t0[1],t0[0]))},
              'out':{'location':[path.points[-1][0],path.points[-1][1],cfg.end_elevation], 'yaw_degrees':math.degrees(math.atan2(t1[1],t1[0]))},
              'collision':collision}
    return mesh,metadata


def library_specs():
    base=Config();specs=[]
    def put(name,kind='STRAIGHT',cfg=None,**kw):
        specs.append({'name':name,'kind':kind,'config':asdict(cfg or base),'path':kw})
    for l in (2,4,8):put(f'SM_SW01_Straight_{l:02d}m',length_m=l)
    for a in (15,30,45,90):
        for sign,label in ((1,'L'),(-1,'R')):
            put(f'SM_SW01_Arc_R4_{a:02d}{label}','ARC',radius=4.,angle=a*sign)
    for a in (45,90):
        for sign,label in ((1,'L'),(-1,'R')):
            put(f'SM_SW01_Corner_{a:02d}{label}','CORNER',angle=a*sign,leg=3.)
    put('SM_SW01_SCurve_R4_45','S_CURVE',radius=4.,angle=45.)
    for pattern,pa in [('RUNNING',0.),('STACK',0.),('BASKET',0.),('SLABS',0.)]:
        cfg=replace(base,pattern=pattern,pattern_angle=pa)
        put('SM_SW01_'+pattern+'_04m',cfg=cfg,length_m=4.)
    put('SM_SW01_Tactile_04m',cfg=replace(base,tactile=True,pattern='RUNNING',pattern_angle=0.),length_m=4.)
    put('SM_SW01_Tactile_Arc90','ARC',cfg=replace(base,tactile=True),radius=4.,angle=90.)
    put('SM_SW01_Drain_04m',cfg=replace(base,drainage=True,pattern='RUNNING',pattern_angle=0.),length_m=4.)
    put('SM_SW01_Ramp_02m','RAMP',cfg=replace(base,end_elevation=-.16,pattern='RUNNING',pattern_angle=0.),length_m=2.)
    put('SM_SW01_Plaza_Slabs',cfg=replace(base,width=4.,pattern='SLABS',pattern_angle=0.,paver_length=.80,paver_width=.40),length_m=4.)
    return specs


def build_spec(spec):
    cfg=Config(**spec['config']);cfg.validate()
    params=dict(spec.get('path',{}));params.setdefault('step',cfg.curve_step)
    path=make_path(spec.get('kind','STRAIGHT'),**params)
    if spec.get('kind') in ('ARC','S_CURVE') and params.get('radius',4.) <= cfg.width/2+.25:
        raise ValueError('Radius must exceed half the total width by at least 0.25 m.')
    return build_module(spec['name'],path,cfg)


def transform_points(vertices,location=(0.,0.,0.),yaw=0.):
    a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
    return [(location[0]+c*x-s*y,location[1]+s*x+c*y,location[2]+z) for x,y,z in vertices]


def chain_layout(modules,sequence,start=(0.,0.,0.),yaw=0.):
    out=[];p=list(start);heading=yaw
    for name in sequence:
        m=modules[name];a=heading-m['in']['yaw_degrees']
        q=transform_points([m['in']['location']],(0,0,0),a)[0]
        origin=[p[i]-q[i] for i in range(3)]
        out.append({'module':name,'location_m':origin,'yaw_blender_degrees':a})
        p=list(transform_points([m['out']['location']],origin,a)[0]);heading=a+m['out']['yaw_degrees']
    return out
