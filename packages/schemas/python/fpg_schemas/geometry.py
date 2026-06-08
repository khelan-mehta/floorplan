"""Geometry invariants (Phase 02), mirroring the TypeScript ``geometry.ts``.

Deterministic, dependency-free. Coordinates are integer millimetres.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

Point = tuple[float, float]


@dataclass(frozen=True)
class GeometryIssue:
    code: str  # too_few_points | non_integer | outer_not_ccw | hole_not_cw | self_intersection | zero_area
    message: str
    path: str


def signed_area(points: list[Point]) -> float:
    """Shoelace signed area (mm²). Positive = CCW, negative = CW."""
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return total / 2


def is_ccw(points: list[Point]) -> bool:
    return signed_area(points) > 0


def _orient(a: Point, b: Point, c: Point) -> int:
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 1 if v > 0 else -1 if v < 0 else 0


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    return (
        min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    )


def _segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    o1, o2 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    o3, o4 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p2, p3):
        return True
    if o2 == 0 and _on_segment(p1, p2, p4):
        return True
    if o3 == 0 and _on_segment(p3, p4, p1):
        return True
    return bool(o4 == 0 and _on_segment(p3, p4, p2))


def ring_self_intersects(points: list[Point]) -> bool:
    n = len(points)
    for i in range(n):
        a1, a2 = points[i], points[(i + 1) % n]
        for j in range(i + 1, n):
            if (i + 1) % n == j or (j + 1) % n == i:
                continue
            b1, b2 = points[j], points[(j + 1) % n]
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False


def lint_polygon(polygon: dict[str, Any], path: str) -> list[GeometryIssue]:
    issues: list[GeometryIssue] = []
    for ri, ring in enumerate(polygon["rings"]):
        rpath = f"{path}/rings/{ri}"
        pts: list[Point] = [(p[0], p[1]) for p in ring["points"]]
        if len(pts) < 3:
            issues.append(GeometryIssue("too_few_points", "ring needs >= 3 points", rpath))
            continue
        if any(not float(x).is_integer() or not float(y).is_integer() for x, y in pts):
            issues.append(GeometryIssue("non_integer", "coordinates must be integer mm", rpath))
        area = signed_area(pts)
        if area == 0:
            issues.append(GeometryIssue("zero_area", "ring has zero area", rpath))
        elif ri == 0 and area < 0:
            issues.append(GeometryIssue("outer_not_ccw", "outer ring must be CCW", rpath))
        elif ri > 0 and area > 0:
            issues.append(GeometryIssue("hole_not_cw", "hole ring must be CW", rpath))
        if ring_self_intersects(pts):
            issues.append(GeometryIssue("self_intersection", "ring self-intersects", rpath))
    return issues


def lint_boundary(boundary: dict[str, Any]) -> list[GeometryIssue]:
    issues: list[GeometryIssue] = []
    for li, level in enumerate(boundary["levels"]):
        issues += lint_polygon(level["outline"], f"/levels/{li}/outline")
        for ci, core in enumerate(level.get("cores", [])):
            issues += lint_polygon(core, f"/levels/{li}/cores/{ci}")
        for vi, void in enumerate(level.get("voids", [])):
            issues += lint_polygon(void, f"/levels/{li}/voids/{vi}")
    site = boundary.get("site")
    if site:
        issues += lint_polygon(site["parcel_polygon"], "/site/parcel_polygon")
    return issues


def lint_plan(plan: dict[str, Any]) -> list[GeometryIssue]:
    issues: list[GeometryIssue] = []
    for li, level in enumerate(plan["levels"]):
        for ri, room in enumerate(level["rooms"]):
            issues += lint_polygon(room["polygon"], f"/levels/{li}/rooms/{ri}/polygon")
    return issues
