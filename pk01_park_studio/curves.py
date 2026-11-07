"""Dependency-free 2D curve toolkit for flowing park paths.
Centripetal Catmull-Rom splines, tangent-arc fillets, envelope meanders and
curvature-adaptive resampling. Metres, XY plane. Visual scenery, not road design.
"""
from __future__ import annotations
import math

EPS = 1e-9


def _sub(a, b): return (a[0]-b[0], a[1]-b[1])
def _add(a, b): return (a[0]+b[0], a[1]+b[1])
def _mul(a, k): return (a[0]*k, a[1]*k)
def _len(a): return math.hypot(a[0], a[1])
def _unit(a):
    n = _len(a)
    if n < EPS: raise ValueError('Zero-length curve segment.')
    return (a[0]/n, a[1]/n)
def _cross(a, b): return a[0]*b[1]-a[1]*b[0]
def _dot(a, b): return a[0]*b[0]+a[1]*b[1]


def dedupe(points, tolerance=1e-6):
    out = []
    for p in points:
        p = (float(p[0]), float(p[1]))
        if not all(math.isfinite(v) for v in p): raise ValueError('Non-finite curve point.')
        if not out or _len(_sub(p, out[-1])) > tolerance: out.append(p)
    return out


def polyline_length(points):
    return sum(_len(_sub(b, a)) for a, b in zip(points, points[1:]))


def cumulative(points):
    dist = [0.]
    for a, b in zip(points, points[1:]): dist.append(dist[-1]+_len(_sub(b, a)))
    return dist


def sample(points, s, dist=None):
    """Point and unit tangent at arc length s along a polyline."""
    dist = dist or cumulative(points)
    s = max(0., min(dist[-1], s))
    for i in range(len(points)-1):
        if dist[i+1] >= s or i == len(points)-2:
            seg = dist[i+1]-dist[i]
            t = 0. if seg < EPS else (s-dist[i])/seg
            a, b = points[i], points[i+1]
            return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t), _unit(_sub(b, a))
    raise ValueError('Cannot sample an empty polyline.')


def slice_polyline(points, s0, s1, dist=None):
    """Sub-polyline between arc lengths s0 < s1, keeping interior vertices."""
    dist = dist or cumulative(points)
    if s1 <= s0: raise ValueError('Empty polyline slice.')
    out = [sample(points, s0, dist)[0]]
    out += [p for p, s in zip(points, dist) if s0+1e-7 < s < s1-1e-7]
    out.append(sample(points, s1, dist)[0])
    return dedupe(out, 1e-7)


def catmull_rom(points, step=.3, alpha=.5):
    """Centripetal Catmull-Rom through every control point (no cusps/self-loops)."""
    pts = dedupe(points)
    if len(pts) < 3: return pts
    ext = [_add(pts[0], _sub(pts[0], pts[1]))]+pts+[_add(pts[-1], _sub(pts[-1], pts[-2]))]
    out = [pts[0]]
    for i in range(1, len(ext)-2):
        p0, p1, p2, p3 = ext[i-1], ext[i], ext[i+1], ext[i+2]
        t0 = 0.
        t1 = t0+max(_len(_sub(p1, p0)), EPS)**alpha
        t2 = t1+max(_len(_sub(p2, p1)), EPS)**alpha
        t3 = t2+max(_len(_sub(p3, p2)), EPS)**alpha
        n = max(2, math.ceil(_len(_sub(p2, p1))/step))
        for k in range(1, n+1):
            t = t1+(t2-t1)*k/n
            def lerp(pa, pb, ta, tb):
                d = tb-ta
                return pa if abs(d) < EPS else _add(_mul(pa, (tb-t)/d), _mul(pb, (t-ta)/d))
            a1 = lerp(p0, p1, t0, t1); a2 = lerp(p1, p2, t1, t2); a3 = lerp(p2, p3, t2, t3)
            b1 = lerp(a1, a2, t0, t2); b2 = lerp(a2, a3, t1, t3)
            out.append(lerp(b1, b2, t1, t2))
    return dedupe(out)


def fillet_polyline(points, radius, step=.25):
    """Replace every interior corner with a tangent circular arc.
    The radius is reduced locally so an arc never consumes more than half of a leg.
    """
    pts = dedupe(points)
    if len(pts) < 3 or radius <= 0: return pts
    out = [pts[0]]
    for i in range(1, len(pts)-1):
        a, b, c = pts[i-1], pts[i], pts[i+1]
        u = _unit(_sub(a, b)); v = _unit(_sub(c, b))
        turn = math.pi-math.acos(max(-1., min(1., _dot(u, v))))
        if turn < math.radians(.5):
            out.append(b); continue
        half = (math.pi-turn)/2
        leg_limit = .5*min(_len(_sub(a, b)), _len(_sub(c, b)))
        r = min(radius, leg_limit*math.tan(half))
        trim = r/math.tan(half)
        p0 = _add(b, _mul(u, trim)); p1 = _add(b, _mul(v, trim))
        bis = _unit(_add(u, v)); centre = _add(b, _mul(bis, r/math.sin(half)))
        a0 = math.atan2(p0[1]-centre[1], p0[0]-centre[0])
        a1 = math.atan2(p1[1]-centre[1], p1[0]-centre[0])
        sweep = (a1-a0+math.pi) % math.tau-math.pi
        n = max(2, math.ceil(abs(sweep)*r/step))
        out.extend((centre[0]+r*math.cos(a0+sweep*k/n), centre[1]+r*math.sin(a0+sweep*k/n)) for k in range(n+1))
    out.append(pts[-1])
    return dedupe(out)


def meander(a, b, amplitude, waves=1, step=.3, phase=1.):
    """Gentle lateral wave between a and b with zero offset AND zero slope at both ends,
    so the path stays flush and tangent with orthogonal junction arms.
    offset(t) = A * sin(pi t) * sin(waves pi t)
    """
    d = _sub(b, a); L = _len(d)
    if L < EPS: raise ValueError('Meander endpoints coincide.')
    u = _unit(d); n = (-u[1], u[0]); waves = max(1, int(waves))
    count = max(8, math.ceil(L/step))
    out = []
    for k in range(count+1):
        t = k/count
        off = phase*amplitude*math.sin(math.pi*t)*math.sin(waves*math.pi*t)
        out.append(_add(_add(a, _mul(d, t)), _mul(n, off)))
    return out


def safe_meander_amplitude(length, width, waves=1, requested=1.5, min_radius_factor=3.):
    """Clamp amplitude so the minimum centre-line radius stays >= factor * width."""
    if length <= 0 or requested <= 0: return 0.
    k = math.pi/length
    # Upper bound of |offset''| for A sin(kx) sin(nkx): A k^2 (1+n)^2.
    bound = k*k*(1+waves)**2
    limit = 1./(bound*min_radius_factor*max(width, .5))
    return max(0., min(requested, limit, length*.08))


def turn_angle(a, b, c):
    u = _sub(b, a); v = _sub(c, b)
    if _len(u) < EPS or _len(v) < EPS: return 0.
    return math.atan2(_cross(u, v), _dot(u, v))


def resample_adaptive(points, max_step=.45, min_step=.12, max_turn_deg=4.):
    """Arc-length resampling: long samples on straights, dense samples on tight bends.
    Keeps both endpoints exactly; the output has no duplicated points.
    """
    pts = dedupe(points)
    if len(pts) < 2: raise ValueError('Resampling needs two points.')
    dist = cumulative(pts); total = dist[-1]
    if total < EPS: raise ValueError('Zero-length curve.')
    # Local curvature estimate per input vertex.
    curv = [0.]*len(pts)
    for i in range(1, len(pts)-1):
        seg = .5*(dist[i+1]-dist[i-1])
        curv[i] = abs(turn_angle(pts[i-1], pts[i], pts[i+1]))/max(seg, EPS)
    limit = math.radians(max_turn_deg)
    out = [pts[0]]; s = 0.
    while True:
        # Curvature at the current position (nearest vertex).
        j = min(range(len(dist)), key=lambda q: abs(dist[q]-s))
        k = max(curv[max(0, j-1):j+2])
        step = max_step if k < EPS else max(min_step, min(max_step, limit/k))
        s += step
        if s >= total-min_step*.5: break
        out.append(sample(pts, s, dist)[0])
    out.append(pts[-1])
    return dedupe(out)


def min_radius(points):
    """Smallest discrete turning radius along a polyline (inf for a straight line)."""
    best = float('inf')
    for a, b, c in zip(points, points[1:], points[2:]):
        ang = abs(turn_angle(a, b, c))
        if ang < 1e-7: continue
        seg = .5*(_len(_sub(b, a))+_len(_sub(c, b)))
        best = min(best, seg/ang)
    return best


def arc_points(centre, radius, a0, a1, step=.2):
    n = max(2, math.ceil(abs(a1-a0)*radius/step))
    return [(centre[0]+radius*math.cos(a0+(a1-a0)*k/n), centre[1]+radius*math.sin(a0+(a1-a0)*k/n)) for k in range(n+1)]


def polygon_area(poly):
    return .5*sum(_cross(poly[i], poly[(i+1) % len(poly)]) for i in range(len(poly)))


def offset_polygon(poly, distances):
    """Inset a CCW polygon; distances[i] applies to edge poly[i]->poly[i+1].
    Consecutive offset edges are intersected; near-parallel edges are averaged.
    """
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i+1) % n]
        t = _unit(_sub(b, a)); nrm = (-t[1], t[0])
        d = distances[i]
        lines.append((_add(a, _mul(nrm, d)), t))
    out = []
    for i in range(n):
        (p1, t1), (p2, t2) = lines[i-1], lines[i]
        den = _cross(t1, t2)
        if abs(den) < 1e-6:
            out.append(p2)
        else:
            k = _cross(_sub(p2, p1), t2)/den
            out.append(_add(p1, _mul(t1, k)))
    return out
