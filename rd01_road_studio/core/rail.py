"""Centre-line rails and station sampling (spec §3.1).

A rail is a dense plan polyline with heights, parameterised by plan arc length s. Offsets
use the left normal: P(s, t, z) = C(s) + t·N(s) + (0, 0, z). Stations are spaced so the
chord error (sagitta) of the outermost column stays under a tolerance.
"""
from __future__ import annotations
import bisect
import math

Vec3 = tuple[float, float, float]


class Rail:
    def __init__(self, points: list[Vec3], closed: bool = False,
                 end_tangents: tuple[tuple[float, float], tuple[float, float]] | None = None):
        pts: list[Vec3] = []
        for p in points:
            p = (float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0)
            if not all(math.isfinite(c) for c in p):
                raise ValueError('Non-finite rail point.')
            if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 1e-6:
                pts.append(p)
        if len(pts) < 2:
            raise ValueError('A rail needs two distinct points.')
        self.points = pts
        self.dist = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.dist.append(self.dist[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.length = self.dist[-1]
        self.closed = closed
        # Exact design tangents at both ends (arcs, Bézier handles): sampled chords lag by half a
        # step angle, which would leave a kit joint or a junction mouth out of square.
        self.end_tangents = None
        if end_tangents:
            self.end_tangents = tuple(_unit2(t) for t in end_tangents)

    # ------------------------------------------------------------- builders
    @staticmethod
    def line(length: float, start: Vec3 = (0.0, 0.0, 0.0), heading_deg: float = 0.0, grade: float = 0.0) -> 'Rail':
        if length <= 0:
            raise ValueError('Line length must be positive.')
        h = math.radians(heading_deg)
        return Rail([start, (start[0] + length * math.cos(h), start[1] + length * math.sin(h), start[2] + grade * length)])

    @staticmethod
    def arc(radius: float, angle_deg: float, start: Vec3 = (0.0, 0.0, 0.0), step: float = 0.05) -> 'Rail':
        """Circular arc starting along +X, turning left for positive angles."""
        if radius <= 0 or angle_deg == 0:
            raise ValueError('Arc needs a positive radius and a non-zero angle.')
        a = math.radians(abs(angle_deg)); sgn = 1 if angle_deg > 0 else -1
        n = max(8, math.ceil(radius * a / step))
        return Rail([(start[0] + radius * math.sin(a * k / n), start[1] + sgn * radius * (1 - math.cos(a * k / n)), start[2])
                     for k in range(n + 1)], end_tangents=((1.0, 0.0), (math.cos(a), sgn * math.sin(a))))

    @staticmethod
    def from_bezier(segments: list[tuple[Vec3, Vec3, Vec3, Vec3]], step: float = 0.05) -> 'Rail':
        """Cubic Bézier chain (p0, handle_out, handle_in, p1), densely sampled."""
        pts: list[Vec3] = []
        for p0, h0, h1, p1 in segments:
            est = sum(math.dist(a, b) for a, b in ((p0, h0), (h0, h1), (h1, p1)))
            n = max(8, math.ceil(est / step))
            for k in range(0 if not pts else 1, n + 1):
                t = k / n; u = 1 - t
                pts.append(tuple(u ** 3 * p0[i] + 3 * u * u * t * h0[i] + 3 * u * t * t * h1[i] + t ** 3 * p1[i]
                                 for i in range(3)))
        def lead(a, b, c):
            d = (b[0] - a[0], b[1] - a[1])
            return d if math.hypot(*d) > 1e-9 else (c[0] - a[0], c[1] - a[1])   # zero-length handle
        first, last = segments[0], segments[-1]
        return Rail(pts, end_tangents=(lead(first[0], first[1], first[2]),
                                       tuple(-c for c in lead(last[3], last[2], last[1]))))

    # ------------------------------------------------------------- queries
    def _locate(self, s: float) -> tuple[int, float]:
        s = max(0.0, min(self.length, s))
        i = min(bisect.bisect_right(self.dist, s) - 1, len(self.points) - 2)
        seg = self.dist[i + 1] - self.dist[i]
        return i, (s - self.dist[i]) / seg if seg > 0 else 0.0

    def at(self, s: float) -> Vec3:
        i, k = self._locate(s)
        a, b = self.points[i], self.points[i + 1]
        return tuple(a[j] + k * (b[j] - a[j]) for j in range(3))

    def tangent(self, s: float, h: float = 0.05) -> tuple[float, float]:
        """Unit plan tangent: exact at the ends when known, else a central difference."""
        if self.end_tangents:
            if s <= 1e-9:
                return self.end_tangents[0]
            if s >= self.length - 1e-9:
                return self.end_tangents[1]
        a = self.at(max(0.0, s - h)); b = self.at(min(self.length, s + h))
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        if n < 1e-12:
            raise ValueError('Degenerate rail tangent.')
        return dx / n, dy / n

    def curvature(self, s: float, h: float = 0.25) -> float:
        """Signed plan curvature (+ = turning left)."""
        h = min(h, self.length / 4)
        t0 = self.tangent(max(0.0, s - h), h / 4); t1 = self.tangent(min(self.length, s + h), h / 4)
        span = min(self.length, s + h) - max(0.0, s - h)
        ang = math.atan2(t0[0] * t1[1] - t0[1] * t1[0], t0[0] * t1[0] + t0[1] * t1[1])
        return ang / span if span > 0 else 0.0

    def offset_point(self, s: float, t: float, z: float, tangent: tuple[float, float] | None = None) -> Vec3:
        c = self.at(s)
        tx, ty = tangent or self.tangent(s)
        return (c[0] - ty * t, c[1] + tx * t, c[2] + z)

    def max_curvature(self, s0: float, s1: float, probes: int = 6) -> float:
        return max(abs(self.curvature(s0 + (s1 - s0) * k / probes)) for k in range(probes + 1))


def _unit2(v) -> tuple[float, float]:
    n = math.hypot(v[0], v[1])
    if n < 1e-12:
        raise ValueError('Zero-length end tangent.')
    return (v[0] / n, v[1] / n)


def station_spacing(radius: float, reach: float, tol: float = 0.01, max_step: float = 1.0) -> float:
    """Largest step whose chord error on the outer column stays below tol (m)."""
    if not math.isfinite(radius) or radius > 1e6:
        return max_step
    r_out = radius + reach
    return max(0.05, min(max_step, math.sqrt(8.0 * r_out * tol)))


def sample_stations(rail: Rail, reach: float, max_step: float = 1.0, tol: float = 0.01,
                    uniform: bool = False) -> list[float]:
    """Plan stations from 0 to L. `uniform` gives equal spacing (spline-mesh kit pieces)."""
    L = rail.length
    if uniform:
        kmax = max(rail.max_curvature(0, L, 24), 1e-9)
        h = station_spacing(1 / kmax, reach, tol, max_step)
        n = max(2, math.ceil(L / h - 1e-9))
        return [L * k / n for k in range(n + 1)]
    out = [0.0]
    while out[-1] < L - 1e-9:
        s = out[-1]
        k = rail.max_curvature(s, min(L, s + max_step), 4)
        h = station_spacing(1 / k if k > 1e-9 else float('inf'), reach, tol, max_step)
        out.append(min(L, s + h))
    if len(out) > 2 and out[-1] - out[-2] < 0.35 * (out[-2] - out[-3]):
        # Merge a sliver last step into an even split of the last two.
        a = out[-3]; out = out[:-2] + [(a + L) / 2, L]
    for a, b in zip(out, out[1:]):
        if b - a <= 1e-6:
            raise ValueError('Station sampling produced a zero-length step.')
    return out


def check_offset(rail: Rail, reach: float) -> None:
    """Refuse a rail whose inner columns would fold over (radius ≤ reach)."""
    for k in range(0, 41):
        s = rail.length * k / 40
        kap = abs(rail.curvature(s))
        if kap > 1e-9 and 1 / kap <= reach * 1.02:
            raise ValueError(f'Curve radius {1 / kap:.2f} m at s={s:.1f} m is smaller than the road half-width '
                             f'{reach:.2f} m; widen the curve or use a junction/roundabout piece.')
