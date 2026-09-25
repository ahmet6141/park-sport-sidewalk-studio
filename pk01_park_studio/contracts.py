"""Portable affine coordinate contract. Source metres -> measured UE import basis.
No assumed FBX left/right orientation. Supports positive scale and rotations, rejects shear.
"""
import math

def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def transpose(a):return [list(x) for x in zip(*a)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def det(a):return a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0])
def quaternion(r):
    t=r[0][0]+r[1][1]+r[2][2]
    if t>0:
        s=math.sqrt(t+1)*2;w=.25*s;x=(r[2][1]-r[1][2])/s;y=(r[0][2]-r[2][0])/s;z=(r[1][0]-r[0][1])/s
    elif r[0][0]>r[1][1] and r[0][0]>r[2][2]:
        s=math.sqrt(1+r[0][0]-r[1][1]-r[2][2])*2;w=(r[2][1]-r[1][2])/s;x=.25*s;y=(r[0][1]+r[1][0])/s;z=(r[0][2]+r[2][0])/s
    elif r[1][1]>r[2][2]:
        s=math.sqrt(1+r[1][1]-r[0][0]-r[2][2])*2;w=(r[0][2]-r[2][0])/s;x=(r[0][1]+r[1][0])/s;y=.25*s;z=(r[1][2]+r[2][1])/s
    else:
        s=math.sqrt(1+r[2][2]-r[0][0]-r[1][1])*2;w=(r[1][0]-r[0][1])/s;x=(r[0][2]+r[2][0])/s;y=(r[1][2]+r[2][1])/s;z=.25*s
    n=math.sqrt(x*x+y*y+z*z+w*w);return (x/n,y/n,z/n,w/n)

def convert_matrix(matrix,basis):
    if len(matrix)!=4 or any(len(row)!=4 for row in matrix):raise ValueError('Expected a row-major 4x4 matrix.')
    a=[row[:3] for row in matrix[:3]];t=[row[3] for row in matrix[:3]]
    if any(not math.isfinite(x) for row in matrix for x in row):raise ValueError('Nonfinite transform.')
    out=mul(mul(basis,a),transpose(basis));cols=transpose(out);scale=[math.sqrt(dot(c,c)) for c in cols]
    if min(scale)<1e-7:raise ValueError('Zero scale cannot be exported.')
    rot=[[out[i][j]/scale[j] for j in range(3)] for i in range(3)]
    rc=transpose(rot)
    if any(abs(dot(rc[i],rc[j])-(1. if i==j else 0.))>1e-4 for i in range(3) for j in range(3)):
        raise ValueError('Sheared transform: apply transforms / remove non-uniformly scaled rotated parents.')
    if det(rot)<.99:raise ValueError('Mirrored transform: apply negative scale before export.')
    location=[100*dot(row,t) for row in basis]
    return location,quaternion(rot),scale

def infer_basis(x_bounds,y_bounds):
    axes=[]
    for bounds,length,ztop in ((x_bounds,200.,40.),(y_bounds,300.,60.)):
        lo,hi=bounds;extent=[hi[i]-lo[i] for i in range(3)]
        major=max(range(2),key=lambda i:extent[i]);other=1-major
        if abs(extent[major]-length)>1 or abs(extent[other]-20)>1 or abs(hi[2]-ztop)>1 or abs(lo[2])>1:
            raise ValueError('FBX unit/pivot calibration failed: '+str(extent)+' cm. Preserve source units and pivots.')
        center=(lo[major]+hi[major])/2
        if abs(abs(center)-length/2)>1:raise ValueError('Calibration pivot was recentered. Disable transform-to-absolute/centering.')
        v=[0.,0.,0.];v[major]=1 if center>0 else -1;axes.append(v)
    if abs(dot(axes[0],axes[1]))>.01:raise ValueError('Cannot infer orthogonal XY import axes.')
    return transpose([axes[0],axes[1],[0.,0.,1.]])
