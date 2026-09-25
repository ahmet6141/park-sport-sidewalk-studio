"""Original parametric furniture, sports equipment and botanical starter meshes."""
from __future__ import annotations
import math,random
from .geometry import Mesh,MAT,rect,ellipse,arc,TAU,vadd,vmul,vsub,vunit


def bench():
    m=Mesh('SM_PK01_Bench_200');wood,metal=MAT['Timber'],MAT['Steel']
    for x in (-.72,.72):
        m.box((x,0,.205),(.065,.49,.41),metal,.007)
        m.box((x,.19,.61),(.055,.055,.61),metal,.006)
        m.box((x,0,.43),(.065,.61,.05),metal,.006)
        m.add_collision_box((x,0,.22),(.09,.52,.44))
    for y in (-.22,-.11,0,.11,.22):m.box((0,y,.46),(2.,.097,.055),wood,.008,uvscale=.7)
    for z in (.61,.74,.87):m.box((0,.225,z),(2.,.05,.11),wood,.007,uvscale=.7)
    for x in (-.89,.89):
        m.cylinder((x,-.18,.47),(x,-.18,.66),.019,metal,n=8)
        m.cylinder((x,-.18,.66),(x,.19,.66),.022,metal,n=8)
    m.add_collision_box((0,0,.455),(2,.55,.10));m.add_collision_box((0,.22,.72),(2,.1,.36))
    return m

def pergola():
    m=Mesh('SM_PK01_Pergola_6x5');wood,metal=MAT['Timber'],MAT['Steel']
    for x in (-2.8,2.8):
        for y in (-2.2,2.2):
            m.box((x,y,1.5),(.16,.16,3.),metal,.009)
            m.box((x,y,.025),(.29,.29,.05),metal,.004)
            m.add_collision_box((x,y,1.5),(.18,.18,3.))
    for y in (-2.2,2.2):m.box((0,y,3.05),(6.3,.16,.22),wood,.01)
    for i in range(26):m.box((-3+i*.24,0,3.21),(.095,5.1,.20),wood,.007)
    return m

def bin_prop():
    m=Mesh('SM_PK01_Bin_090');metal=MAT['Steel']
    m.cylinder((0,0,.08),(0,0,.74),.25,metal,n=24)
    for i in range(18):
        a=i*TAU/18;x=.26*math.cos(a);y=.26*math.sin(a)
        m.box((x,y,.43),(.04,.04,.7),MAT['Timber'],.004)
    m.cylinder((0,0,.80),(0,0,.85),.29,metal,n=24)
    for x in (-.22,.22):m.cylinder((x,0,.71),(x,0,.83),.019,metal,n=8)
    m.add_collision_box((0,0,.45),(.6,.6,.9));return m

def light_pole():
    m=Mesh('SM_PK01_PoleLight_5m');s=MAT['Steel']
    m.cylinder((0,0,0),(0,0,4.7),.075,s,r2=.045,n=14)
    m.box((.36,0,4.72),(.87,.12,.085),s,.007)
    m.box((.57,0,4.67),(.54,.09,.015),MAT['Emission'],.002)
    m.box((0,0,.03),(.25,.25,.06),s,.004)
    m.add_collision_box((0,0,2.3),(.18,.18,4.6));return m

def bollard():
    m=Mesh('SM_PK01_BollardLight_09m')
    m.cylinder((0,0,0),(0,0,.9),.08,MAT['Steel'],n=12)
    m.cylinder((0,0,.73),(0,0,.81),.083,MAT['Emission'],n=12)
    m.add_collision_box((0,0,.45),(.17,.17,.9));return m

def planter():
    m=Mesh('SM_PK01_Planter_4x15');c=MAT['Curb']
    for y in (-.70,.70):m.box((0,y,.24),(4.,.12,.48),c,.016)
    for x in (-1.94,1.94):m.box((x,0,.24),(.12,1.3,.48),c,.016)
    m.box((0,0,.37),(3.76,1.26,.07),MAT['Mulch'])
    m.add_collision_box((0,0,.24),(4,1.5,.48));return m

def bike_rack():
    m=Mesh('SM_PK01_BikeRack_5');s=MAT['Steel']
    for x in (-1.2,-.6,0,.6,1.2):
        m.cylinder((x,-.30,.02),(x,-.30,.70),.026,s,n=10)
        m.cylinder((x,.30,.02),(x,.30,.70),.026,s,n=10)
        pts=[(x,-.30*math.cos(a),.70+.30*math.sin(a)) for a in [i*math.pi/16 for i in range(17)]]
        m.tube(pts,.026,s,n=8)
        m.add_collision_box((x,0,.5),(.06,.66,1.))
    return m

def picnic():
    m=Mesh('SM_PK01_Picnic_220')
    for y in [i*.11-.385 for i in range(8)]:m.box((0,y,.75),(2.2,.095,.05),MAT['Timber'],.006)
    for s in (-1,1):
        for y in (s*.73,s*.85,s*.97):m.box((0,y,.45),(2.2,.1,.045),MAT['Timber'],.007)
    for x in (-.75,.75):
        for s in (-1,1):m.cylinder((x,s*.8,0),(x,s*.22,.72),.042,MAT['Steel'],n=8)
        m.box((x,0,.405),(.09,2.,.07),MAT['Steel'],.005)
    m.add_collision_box((0,0,.75),(2.2,.85,.08))
    for s in (-1,1):m.add_collision_box((0,s*.85,.45),(2.2,.37,.08))
    return m

def goal(width=7.32,height=2.44,depth=2.):
    key=f'{width:g}_{height:g}'.replace('.','p');m=Mesh('SM_PK01_Goal_'+key);white=MAT['Line']
    for y in (-width/2,width/2):
        m.cylinder((0,y,0),(0,y,height),.06,white,n=12)
        m.cylinder((0,y,height),(depth,y,height*.74),.025,MAT['Steel'],n=8)
        m.cylinder((depth,y,0),(depth,y,height*.74),.025,MAT['Steel'],n=8)
        m.cylinder((0,y,.02),(depth,y,.02),.025,MAT['Steel'],n=8)
        m.add_collision_box((0,y,height/2),(.13,.13,height))
    m.cylinder((0,-width/2,height),(0,width/2,height),.06,white,n=12)
    m.add_collision_box((0,0,height),(.13,width,.13))
    # Small opaque cords, deliberately no rectangular collision through the mouth.
    for j in range(int(width/.17)+1):
        y=-width/2+width*j/max(1,int(width/.17))
        m.tube([(0,y,height),(depth,y,height*.74),(depth,y,.05)],.0035,MAT['Net'],n=4)
    for j in range(1,int(height*.74/.17)+1):
        z=j*.17;m.cylinder((depth,-width/2,z),(depth,width/2,z),.0035,MAT['Net'],n=4)
    for s in (-1,1):
        y=s*width/2
        for j in range(1,int(depth/.17)+1):
            x=depth*j/max(1,int(depth/.17));top=height*(1-.26*x/depth)
            m.cylinder((x,y,.03),(x,y,top),.0035,MAT['Net'],n=4)
    return m

def hoop():
    """Local hoop centre is x=0, y=0, z=3.05. Post extends in +X."""
    m=Mesh('SM_PK01_Hoop_305');s=MAT['Steel'];w=MAT['Line']
    m.box((2.75,0,.09),(.95,.90,.18),s,.025)
    m.cylinder((2.75,0,.15),(2.55,0,3.40),.11,s,r2=.08,n=12)
    m.cylinder((2.55,0,3.40),(.38,0,3.6),.075,s,n=10)
    m.box((.375,0,3.475),(.036,1.8,1.05),MAT['Glass'],.007)
    for y in (-.91,.91):m.box((.4,y,3.475),(.05,.045,1.08),s,.004)
    for z in (2.96,3.995):m.box((.4,0,z),(.05,1.84,.045),s,.004)
    for y in (-.295,.295):m.box((.345,y,3.27),(.01,.05,.45),w)
    for z in (3.045,3.495):m.box((.345,0,z),(.01,.64,.05),w)
    pts=[(.225*math.cos(i*TAU/48),.225*math.sin(i*TAU/48),3.05) for i in range(49)]
    m.tube(pts,.01,MAT['EPDM_Terracotta'],n=6)
    m.box((.27,0,3.045),(.19,.10,.025),MAT['EPDM_Terracotta'])
    for i in range(16):
        a=i*TAU/16
        m.tube([(.225*math.cos(a),.225*math.sin(a),3.035),(.14*math.cos(a+.14),.14*math.sin(a+.14),2.70),(.15*math.cos(a),.15*math.sin(a),2.63)],.003,MAT['Net'],n=4)
    m.add_collision_box((2.7,0,1.6),(.3,.3,3.2));return m

def net(width=12.8,height=1.07,middle=.914):
    m=Mesh(f'SM_PK01_Net_{width:g}_{height:g}'.replace('.','p'));s=MAT['Steel']
    for y in (-width/2,width/2):
        m.cylinder((0,y,0),(0,y,height+.04),.04,s,n=12)
        m.add_collision_box((0,y,height/2),(.10,.10,height))
    samples=max(10,int(width/.12))
    for i in range(samples+1):
        y=-width/2+width*i/samples;top=middle+(height-middle)*(2*y/width)**2
        m.cylinder((0,y,max(.07,top-1.)),(0,y,top),.0028,MAT['Net'],n=4)
    for j in range(8):
        pts=[]
        for i in range(25):
            y=-width/2+width*i/24;top=middle+(height-middle)*(2*y/width)**2
            pts.append((0,y,max(.07,top-j*.11)))
        m.tube(pts,.0028,MAT['Net'],n=4)
    tape=[(0,-width/2+width*i/48,middle+(height-middle)*(-1+2*i/48)**2) for i in range(49)]
    m.tube(tape,.018,MAT['Line'],n=6);return m

def fitness():
    m=Mesh('SM_PK01_Calisthenics_6x4');s=MAT['Steel'];a=MAT['EPDM_Terracotta']
    for x,h in ((-2.4,2.5),(-.8,2.2),(.8,1.8)):
        for y in (-.9,.9):m.cylinder((x,y,0),(x,y,h),.06,s,n=10)
        m.cylinder((x,-.9,h),(x,.9,h),.028,a,n=10)
        for y in (-.9,.9):m.add_collision_box((x,y,h/2),(.14,.14,h))
    for x in (1.8,2.5):
        for y in (-1.5,1.5):m.cylinder((x,y,0),(x,y,1.1),.045,s,n=10)
        m.cylinder((x,-1.5,1.1),(x,1.5,1.1),.035,a,n=10)
    return m

def table_tennis():
    m=Mesh('SM_PK01_TableTennis_274');s=MAT['Steel'];w=MAT['Line']
    m.box((0,0,.73),(2.74,1.525,.06),MAT['CourtBlue'],.009)
    m.line(rect(0,0,2.72,1.505),.02,.761,w,True);m.line([(-1.37,0),(1.37,0)],.003,.762,w)
    for x in (-.85,.85):
        for y in (-.51,.51):m.box((x,y,.35),(.07,.07,.70),s,.005)
    for y in (-.80,.80):m.cylinder((0,y,.76),(0,y,.94),.012,s,n=8)
    for j in range(9):m.cylinder((0,-.8,.78+j*.018),(0,.8,.78+j*.018),.0018,MAT['Net'],n=4)
    for j in range(45):m.cylinder((0,-.8+j*1.6/44,.78),(0,-.8+j*1.6/44,.932),.0018,MAT['Net'],n=4)
    m.add_collision_box((0,0,.73),(2.74,1.525,.06));return m

def fence(length,width,height=3.,gate=4.4):
    m=Mesh(f'SM_PK01_Fence_{length:g}_{width:g}_{height:g}_{gate:g}'.replace('.','p'));s=MAT['Steel']
    sides=[((-length/2,-width/2),(length/2,-width/2)),((-length/2,-width/2),(-length/2,width/2)),((length/2,-width/2),(length/2,width/2)),((-length/2,width/2),(-gate/2,width/2)),((gate/2,width/2),(length/2,width/2))]
    for a,b in sides:
        L=math.dist(a,b)
        for i in range(math.ceil(L/2)+1):
            t=i/math.ceil(L/2);x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
            m.cylinder((x,y,0),(x,y,height),.035,s,n=6)
        for z in (.12,height*.5,height):m.cylinder((*a,z),(*b,z),.017,s,n=6)
        n=max(1,int(L/.25))
        for i in range(n+1):
            t=i/n;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
            m.cylinder((x,y,.13),(x,y,height-.03),.0028,s,n=4)
        for j in range(1,int(height/.25)):m.cylinder((*a,j*.25),(*b,j*.25),.0028,s,n=4)
        cx=(a[0]+b[0])/2;cy=(a[1]+b[1])/2
        m.add_collision_box((cx,cy,height/2),(max(.1,abs(b[0]-a[0])),max(.1,abs(b[1]-a[1])),height))
    return m

def tree(kind='BROADLEAF',seed=41,detail='BALANCED'):
    """Editable botanical starters: actual branches + curved leaf silhouettes (no photos)."""
    rng=random.Random(seed);nleaf={'DRAFT':600,'BALANCED':2600,'HERO':6500}[detail]
    m=Mesh(f'SM_PK01_Tree_{kind}_{seed}_{detail}');b=MAT['Bark']
    height=8.8 if kind=='CYPRESS' else (9.2 if kind=='BIRCH' else 7.8)
    radii=(.21,.11,.035) if kind!='CYPRESS' else (.18,.10,.02)
    trunk=[(0,0,0),(.11,.05,height*.46),(-.09,.09,height*.83),(.10,.06,height)]
    for i in range(3):m.cylinder(trunk[i],trunk[i+1],radii[i],b,r2=max(.016,radii[i]*.56),n=10,tint=(.93,1.,.96) if kind=='BIRCH' else (1,1,1))
    tips=[]
    branches=26 if kind=='CYPRESS' else 20
    for i in range(branches):
        a=i*2.39996+rng.uniform(-.4,.4);z=height*(.25+.67*i/branches)
        reach=(1.65*(1-z/height)+.3) if kind=='CYPRESS' else (2.85*(1-abs(z/height-.58))+.3)
        start=(.02,.03,z);end=(reach*math.cos(a),reach*math.sin(a),z+rng.uniform(.25,1.2))
        m.cylinder(start,end,.046 if kind!='CYPRESS' else .027,b,r2=.008,n=7)
        for k in range(3):
            t=.48+k*.23;mid=tuple(start[j]+(end[j]-start[j])*t for j in range(3))
            ang=a+(-1 if k%2 else 1)*rng.uniform(.5,1.2)
            tip=(mid[0]+.6*math.cos(ang),mid[1]+.6*math.sin(ang),mid[2]+.35)
            m.cylinder(mid,tip,.009,b,r2=.0035,n=5);tips.append(tip)
    for i in range(nleaf):
        tip=tips[rng.randrange(len(tips))]
        spread=.48 if kind=='CYPRESS' else .82
        p=(tip[0]+rng.gauss(0,spread),tip[1]+rng.gauss(0,spread),tip[2]+rng.gauss(.05,spread*.58))
        if kind=='CYPRESS':
            maxr=max(.38,1.75*(1-p[2]/height)+.45);r=math.hypot(p[0],p[1])
            if r>maxr:p=(p[0]*maxr/r,p[1]*maxr/r,p[2])
        a=rng.uniform(0,TAU);axis=(math.cos(a),math.sin(a),rng.uniform(-.15,.9))
        size=rng.uniform(.23,.38) if kind=='BIRCH' else rng.uniform(.31,.54)
        if kind=='CYPRESS':size*=1.5
        tint=(rng.uniform(.75,1.05),rng.uniform(.83,1.08),rng.uniform(.55,.85))
        m.leaf(p,axis,size,size*(.28 if kind=='CYPRESS' else .63),rng.uniform(-.75,.75),tint=tint)
    # Root flare; trunk collision does NOT enclose the canopy.
    for a in (0,1.4,2.9,4.5):m.cylinder((0,0,.37),(.45*math.cos(a),.45*math.sin(a),.03),.09,b,r2=.045,n=7)
    m.add_collision_box((0,0,height*.3),(.40,.40,height*.6));m.meta['foliage']=True
    m.meta['starter_geometry']=True;m.meta['species']=kind;return m

def shrub(seed=0,flower=False):
    rng=random.Random(seed);m=Mesh(f'SM_PK01_{"Flower" if flower else "Shrub"}_{seed}')
    for i in range(100 if flower else 180):
        a=rng.uniform(0,TAU);r=rng.random()**.5*.52;z=rng.uniform(.15,.7)
        p=(r*math.cos(a),r*math.sin(a),z)
        m.leaf(p,(math.cos(a),math.sin(a),.45),rng.uniform(.15,.28),.12,rng.uniform(-.8,.8),tint=(.85,1.,.75))
        if flower and i%4==0:
            for k in range(5):
                a=k*TAU/5;m.leaf((p[0],p[1],z+.08),(math.cos(a),math.sin(a),.1),.07,.05,0,MAT['Flower'],(1.,rng.uniform(.6,1),.85))
    m.meta['foliage']=True;return m

def rock(seed=0):
    rng=random.Random(seed);m=Mesh('SM_PK01_ShoreRock_'+str(seed));rings=6;n=12
    # Ring-and-pole topology without zero-area pole triangles.
    m.vertices=[(0,0,.035)];m.colors=[(.9,.95,1)]
    for j in range(1,rings):
        phi=math.pi*j/rings
        for i in range(n):
            a=TAU*i/n;f=rng.uniform(.86,1.12)
            m.vertices.append((math.sin(phi)*math.cos(a)*.60*f,math.sin(phi)*math.sin(a)*.40*f,.035+(1-math.cos(phi))*.27*f))
            m.colors.append((rng.uniform(.8,1),)*3)
    top=len(m.vertices);m.vertices.append((0,0,.59));m.colors.append((1,1,1))
    def f(a,b,c):m.face((a,b,c),tuple((m.vertices[k][0],m.vertices[k][1]) for k in (a,b,c)),MAT['Stone'])
    for i in range(n):
        k=(i+1)%n;f(0,1+k,1+i)
        for j in range(rings-2):
            a=1+j*n+i;b=1+j*n+k;c=b+n;d=a+n;f(a,b,c);f(a,c,d)
        f(top,1+(rings-2)*n+i,1+(rings-2)*n+k)
    return m

def reed(seed=0):
    rng=random.Random(seed);m=Mesh('SM_PK01_Reed_'+str(seed))
    for i in range(14):
        x,y=rng.uniform(-.35,.35),rng.uniform(-.35,.35);h=rng.uniform(.6,1.5)
        m.cylinder((x,y,0),(x+.10,y,h),.007,MAT['Leaf'],r2=.003,n=4,tint=(.88,.89,.45))
        for k in range(2):
            a=rng.uniform(0,TAU);m.leaf((x,y,h*(.2+.25*k)),(math.cos(a),math.sin(a),1.5),h*.65,.055,.1,tint=(.9,1,.6))
    m.meta['foliage']=True;return m
