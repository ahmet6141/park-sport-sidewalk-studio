"""Higher-order modelling primitives on top of the SW01-compatible triangle buffer.
Profile sweeps (curbs, rails, benches) and lathes (poles, bollards, bins) with
hard/soft edge control: smooth groups share vertices, hard edges are split so
bullnoses shade round while arrises stay crisp. Pure Python, no bpy.
"""
from __future__ import annotations
import math
from .vendor import sw01_core as sw

TAU = math.tau


def _columns(count, smooth, closed=True):
    """Map each profile edge to (start_column, end_column).
    A profile vertex is shared only when both neighbouring edges are smooth.
    """
    edges = count if closed else count-1
    cols = []; ids = {}
    def column(vertex, owner):
        key = (vertex, owner)
        if key not in ids: ids[key] = len(cols); cols.append(vertex)
        return ids[key]
    result = []
    for k in range(edges):
        a, b = k, (k+1) % count
        prev_smooth = smooth[(k-1) % edges] if (closed or k > 0) else False
        next_smooth = smooth[(k+1) % edges] if (closed or k < edges-1) else False
        sa = column(a, 'shared' if smooth[k] and prev_smooth else ('edge', k))
        sb = column(b, 'shared' if smooth[k] and next_smooth else ('edge', k))
        result.append((sa, sb))
    return cols, result


def sweep(mesh, rail, normals, profile, mat, smooth=None, zoff=None, tint=(1., 1., 1.),
          uvscale=1., caps=True, label='sweep'):
    """Sweep a closed CCW (u, z) profile along a horizontal rail.
    rail: [(x, y)], normals: lateral vectors (may be miter-scaled) so a vertex is
    rail + normal*u. The CCW profile yields outward faces; caps close both ends.
    """
    if len(rail) != len(normals) or len(rail) < 2: raise ValueError('Sweep rail/normal mismatch.')
    if sw.area(profile) <= 0: raise ValueError('Sweep profile must be counter-clockwise.')
    n = len(profile); smooth = list(smooth or [False]*n); zoff = zoff or [0.]*len(rail)
    cols, edges = _columns(n, smooth, True)
    start = len(mesh.vertices); width = len(cols)
    for (x, y), (nx, ny), dz in zip(rail, normals, zoff):
        for v in cols:
            u, z = profile[v]
            mesh.vertices.append((x+nx*u, y+ny*u, z+dz)); mesh.colors.append(tuple(tint))
    along = [0.]
    for a, b in zip(rail, rail[1:]): along.append(along[-1]+math.hypot(b[0]-a[0], b[1]-a[1]))
    perim = [0.]
    for k in range(n):
        a, b = profile[k], profile[(k+1) % n]; perim.append(perim[-1]+math.hypot(b[0]-a[0], b[1]-a[1]))
    old = getattr(mesh, '_smooth', False)
    for k, (ca, cb) in enumerate(edges):
        if hasattr(mesh, '_smooth'): mesh._smooth = smooth[k]
        va, vb = perim[k]/uvscale, perim[k+1]/uvscale
        for i in range(len(rail)-1):
            a = start+i*width+ca; b = start+i*width+cb; c = b+width; d = a+width
            ua, ub = along[i]/uvscale, along[i+1]/uvscale
            mesh.face((a, b, c), ((ua, va), (ua, vb), (ub, vb)), mat)
            mesh.face((a, c, d), ((ua, va), (ub, vb), (ub, va)), mat)
    if hasattr(mesh, '_smooth'): mesh._smooth = False
    if caps:
        tris = sw.triangulate(profile)
        for ring, flip in ((0, True), (len(rail)-1, False)):
            base = len(mesh.vertices)
            (x, y), (nx, ny), dz = rail[ring], normals[ring], zoff[ring]
            for u, z in profile:
                mesh.vertices.append((x+nx*u, y+ny*u, z+dz)); mesh.colors.append(tuple(tint))
            for a, b, c in tris:
                uv = tuple((profile[q][0]/uvscale, profile[q][1]/uvscale) for q in (a, b, c))
                if flip: mesh.face((base+c, base+b, base+a), (uv[2], uv[1], uv[0]), mat)
                else: mesh.face((base+a, base+b, base+c), uv, mat)
    if hasattr(mesh, '_smooth'): mesh._smooth = old
    mesh.solids.append((start, len(mesh.vertices)-start, label))


def lathe(mesh, profile, mat, segments=24, smooth=None, centre=(0., 0., 0.), tint=(1., 1., 1.),
          uvscale=1., label='lathe'):
    """Revolve an open (r, z) profile around the Z axis.
    Trace the profile from the bottom axis outward and up to the top axis; points
    with r == 0 become poles (triangle fans, no zero-area faces).
    """
    n = len(profile)
    if n < 2: raise ValueError('Lathe profile needs two points.')
    smooth = list(smooth or [True]*(n-1))
    cols, edges = _columns(n, smooth, False)
    start = len(mesh.vertices); rings = {}
    for c, v in enumerate(cols):
        r, z = profile[v]
        if r < 1e-7:
            rings[c] = [len(mesh.vertices)]
            mesh.vertices.append((centre[0], centre[1], centre[2]+z)); mesh.colors.append(tuple(tint))
        else:
            rings[c] = list(range(len(mesh.vertices), len(mesh.vertices)+segments))
            for j in range(segments):
                a = TAU*j/segments
                mesh.vertices.append((centre[0]+r*math.cos(a), centre[1]+r*math.sin(a), centre[2]+z)); mesh.colors.append(tuple(tint))
    rmax = max(r for r, z in profile); circ = TAU*max(rmax, .01)/uvscale
    perim = [0.]
    for a, b in zip(profile, profile[1:]): perim.append(perim[-1]+math.hypot(b[0]-a[0], b[1]-a[1]))
    old = getattr(mesh, '_smooth', False)
    for k, (ca, cb) in enumerate(edges):
        if hasattr(mesh, '_smooth'): mesh._smooth = smooth[k]
        lo, hi = rings[ca], rings[cb]; va, vb = perim[k]/uvscale, perim[k+1]/uvscale
        for j in range(segments):
            j2 = (j+1) % segments; u0, u1 = circ*j/segments, circ*(j+1)/segments
            if len(lo) == 1 and len(hi) == 1: continue
            if len(lo) == 1:
                mesh.face((lo[0], hi[j2], hi[j]), (((u0+u1)/2, va), (u1, vb), (u0, vb)), mat)
            elif len(hi) == 1:
                mesh.face((lo[j], lo[j2], hi[0]), ((u0, va), (u1, va), ((u0+u1)/2, vb)), mat)
            else:
                mesh.face((lo[j], lo[j2], hi[j2]), ((u0, va), (u1, va), (u1, vb)), mat)
                mesh.face((lo[j], hi[j2], hi[j]), ((u0, va), (u1, vb), (u0, vb)), mat)
    if hasattr(mesh, '_smooth'): mesh._smooth = old
    mesh.solids.append((start, len(mesh.vertices)-start, label))


def arc_profile(cx, cz, r, a0, a1, steps):
    return [(cx+r*math.cos(a0+(a1-a0)*k/steps), cz+r*math.sin(a0+(a1-a0)*k/steps)) for k in range(steps+1)]


CURB_STYLES = ('BULLNOSE', 'CHAMFER', 'SQUARE')


def curb_profile(u_outer, u_inner, z0, z1, style='BULLNOSE', radius=.035, chamfer=.008, steps=5):
    """Closed CCW (u, z) kerb section. Outer (exposed) face at u_outer.
    BULLNOSE: rounded exposed arris; CHAMFER: 45 degree splay; SQUARE: pencil-round only.
    Returns (points, smooth_flags).
    """
    if style not in CURB_STYLES: raise ValueError('Unknown curb profile '+str(style))
    w = abs(u_inner-u_outer); h = z1-z0
    if w <= .02 or h <= .02: raise ValueError('Curb section too small.')
    radius = min(radius, w*.45, h*.45); chamfer = min(chamfer, w*.2)
    # Canonical frame: x inward from the exposed face, CCW.
    pts = [(0., z0), (w, z0), (w, z1-chamfer), (w-chamfer, z1)]
    flags = [False, False, False, False]
    if style == 'BULLNOSE':
        arc = arc_profile(radius, z1-radius, radius, math.pi/2, math.pi, steps)
        pts += arc; flags += [True]*steps+[False]
    elif style == 'CHAMFER':
        c = min(.022, w*.25, h*.3)
        pts += [(c, z1), (0., z1-c)]; flags += [False, False]
    else:
        pts += [(chamfer, z1), (0., z1-chamfer)]; flags += [False, False]
    sign = 1. if u_inner > u_outer else -1.
    mapped = [(u_outer+sign*x, z) for x, z in pts]
    if sign < 0:
        # Mirroring reverses orientation: reverse points and re-align edge flags.
        n = len(mapped)
        mapped = mapped[::-1]
        flags = [flags[(n-2-k) % n] for k in range(n)]
    return mapped, flags


def rounded_rect_profile(w, h, r, steps=3, cx=0., cz=0.):
    """Closed CCW section of a w x h rectangle with radius-r rounded arrises (all smooth arcs)."""
    r = min(r, w*.49, h*.49)
    pts = []; flags = []
    corners = [(cx+w/2-r, cz-h/2+r, -math.pi/2), (cx+w/2-r, cz+h/2-r, 0.),
               (cx-w/2+r, cz+h/2-r, math.pi/2), (cx-w/2+r, cz-h/2+r, math.pi)]
    for x, z, a in corners:
        arc = arc_profile(x, z, r, a, a+math.pi/2, steps)
        pts += arc; flags += [True]*steps+[False]
    return pts, flags
