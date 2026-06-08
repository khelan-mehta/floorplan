"""Pure 2D polygon geometry for the layout solver (deterministic, no dependencies).

Coordinates are millimetres. Internally we work in floats (clipping / binary search) and round to
integer mm at the end. Polygons are open rings (first point not repeated), CCW or CW both accepted.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

Pt = tuple[float, float]
Poly = list[Pt]


def to_poly(points: Sequence[Sequence[float]]) -> Poly:
    return [(float(p[0]), float(p[1])) for p in points]


def bbox(poly: Sequence[Pt]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def signed_area(poly: Sequence[Pt]) -> float:
    n = len(poly)
    s = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def area(poly: Sequence[Pt]) -> float:
    return abs(signed_area(poly))


def centroid(poly: Sequence[Pt]) -> Pt:
    n = len(poly)
    a = signed_area(poly)
    if abs(a) < 1e-9:  # degenerate -> average of vertices
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    cx = cy = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    return (cx / (6.0 * a), cy / (6.0 * a))


def round_poly(poly: Sequence[Pt]) -> list[list[int]]:
    """Round to int mm and drop consecutive duplicate / collinear-degenerate points."""
    pts = [(round(x), round(y)) for x, y in poly]
    out: list[tuple[int, int]] = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return [[x, y] for x, y in out]


def clip_axis(poly: Poly, axis: int, cut: float, keep_low: bool) -> Poly:
    """Sutherland-Hodgman clip of a polygon by the half-plane coord<=cut (or >=cut)."""
    if not poly:
        return []

    def inside(p: Pt) -> bool:
        return p[axis] <= cut if keep_low else p[axis] >= cut

    def intersect(a: Pt, b: Pt) -> Pt:
        denom = b[axis] - a[axis]
        t = 0.0 if denom == 0 else (cut - a[axis]) / denom
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    out: Poly = []
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        ina, inb = inside(a), inside(b)
        if ina:
            out.append(a)
            if not inb:
                out.append(intersect(a, b))
        elif inb:
            out.append(intersect(a, b))
    return out


def cut_for_area(poly: Poly, axis: int, frac: float) -> float:
    """Coordinate of an axis-aligned line where the low side holds `frac` of the polygon area."""
    lo, hi = (bbox(poly)[axis], bbox(poly)[axis + 2])
    target = area(poly) * frac
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if area(clip_axis(poly, axis, mid, True)) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def split_by_area(poly: Poly, axis: int, frac: float) -> tuple[Poly, Poly]:
    """Cut the polygon with an axis-aligned line so the low side holds `frac` of the area."""
    cut = cut_for_area(poly, axis, frac)
    return clip_axis(poly, axis, cut, True), clip_axis(poly, axis, cut, False)


def aspect(poly: Poly) -> float:
    """Bounding-box aspect ratio (>=1); large = thin/awkward. inf for degenerate."""
    if area(poly) <= 1.0:
        return float("inf")
    minx, miny, maxx, maxy = bbox(poly)
    w, h = maxx - minx, maxy - miny
    if w <= 0 or h <= 0:
        return float("inf")
    return max(w / h, h / w)


def min_dim(poly: Poly) -> float:
    minx, miny, maxx, maxy = bbox(poly)
    return min(maxx - minx, maxy - miny)


def edges(poly: Sequence[Pt]) -> list[tuple[Pt, Pt]]:
    n = len(poly)
    return [(tuple(poly[i]), tuple(poly[(i + 1) % n])) for i in range(n)]  # type: ignore[misc]


def _dot(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * bx + ay * by


def shared_segment(
    e1: tuple[Pt, Pt], e2: tuple[Pt, Pt], tol: float = 2.0
) -> tuple[float, float, float] | None:
    """If two edges are collinear and overlap, return (overlap_len, lo, hi) measured along e1
    from its first endpoint. Else None. Used for room adjacency + door placement."""
    (a1, a2), (b1, b2) = e1, e2
    dx, dy = a2[0] - a1[0], a2[1] - a1[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None
    ux, uy = dx / length, dy / length
    # perpendicular distance of b1,b2 to e1's line must be ~0 (collinear)
    for b in (b1, b2):
        perp = abs((b[0] - a1[0]) * (-uy) + (b[1] - a1[1]) * ux)
        if perp > tol:
            return None
    tb1 = _dot(b1[0] - a1[0], b1[1] - a1[1], ux, uy)
    tb2 = _dot(b2[0] - a1[0], b2[1] - a1[1], ux, uy)
    lo = max(0.0, min(tb1, tb2))
    hi = min(length, max(tb1, tb2))
    ov = hi - lo
    if ov <= tol:
        return None
    return ov, lo, hi


def point_seg_dist(p: Pt, a: Pt, b: Pt) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    d2 = dx * dx + dy * dy
    if d2 < 1e-9:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / d2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def point_on_boundary(p: Pt, outline_edges: list[tuple[Pt, Pt]], tol: float = 1.5) -> bool:
    return any(point_seg_dist(p, a, b) <= tol for a, b in outline_edges)


def edge_len(e: tuple[Pt, Pt]) -> float:
    (a, b) = e
    return math.hypot(b[0] - a[0], b[1] - a[1])


def point_in_polygon(p: Pt, poly: Sequence[Pt]) -> bool:
    """Ray-cast point-in-polygon test (boundary counts as inside within float noise)."""
    x, y = p
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside
