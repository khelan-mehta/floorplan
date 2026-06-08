"""Derive a deterministic geometry/metric model from a Plan document.

Pure, no I/O. The metric registry maps dotted metric names (used by Rule predicates) to values
computed per element (room/door) or for the whole building.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

EXTERIOR = "__exterior__"


def _bbox(points: list[list[int]]) -> tuple[int, int, int, int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


@dataclass
class RoomMetrics:
    id: str
    type: str
    program_node_id: str | None
    area_mm2: int
    width_mm: int
    depth_mm: int
    window_area_mm2: int
    has_exterior_window: bool
    egress_reachable: bool


@dataclass
class DoorMetrics:
    id: str
    width_mm: int
    room_a: str
    room_b: str


@dataclass
class GeometryModel:
    rooms: list[RoomMetrics]
    doors: list[DoorMetrics]
    ceiling_height_mm: int
    room_by_id: dict[str, RoomMetrics] = field(default_factory=dict)


def build_model(plan: dict[str, Any]) -> GeometryModel:
    rooms: list[RoomMetrics] = []
    doors: list[DoorMetrics] = []
    heights: list[int] = []

    # reachability graph: room ids + EXTERIOR, edges via door/opening connections
    graph: dict[str, set[str]] = {EXTERIOR: set()}

    level = plan["levels"][0] if plan.get("levels") else {"rooms": [], "walls": [], "openings": []}
    for wall in level.get("walls", []):
        heights.append(int(wall.get("height_mm", 2700)))

    window_area: dict[str, int] = {}
    window_exterior: dict[str, bool] = {}

    for op in level.get("openings", []):
        connects = op.get("connects") or []
        kind = op.get("kind")
        if kind == "window":
            room = connects[0] if connects else None
            if room:
                window_area[room] = window_area.get(room, 0) + int(op["width_mm"]) * int(op["height_mm"])
                if EXTERIOR in connects or "exterior" in connects:
                    window_exterior[room] = True
        elif kind in ("door", "opening"):
            a = connects[0] if len(connects) > 0 else None
            b = connects[1] if len(connects) > 1 else None
            b = EXTERIOR if b in ("exterior", "outside") else b
            if a and b:
                graph.setdefault(a, set()).add(b)
                graph.setdefault(b, set()).add(a)
            if kind == "door":
                doors.append(
                    DoorMetrics(id=op["id"], width_mm=int(op["width_mm"]), room_a=a or "", room_b=b or "")
                )

    # rooms that double as entries connect to exterior
    for room in level.get("rooms", []):
        if room["type"] in ("entry", "lobby"):
            graph.setdefault(room["id"], set()).add(EXTERIOR)
            graph[EXTERIOR].add(room["id"])

    reachable = _bfs_reachable(graph, EXTERIOR)

    for room in level.get("rooms", []):
        pts = room["polygon"]["rings"][0]["points"]
        x1, y1, x2, y2 = _bbox(pts)
        w, h = x2 - x1, y2 - y1
        rooms.append(
            RoomMetrics(
                id=room["id"],
                type=room["type"],
                program_node_id=room.get("program_node_id"),
                area_mm2=int(room["area_mm2"]),
                width_mm=min(w, h),
                depth_mm=max(w, h),
                window_area_mm2=window_area.get(room["id"], 0),
                has_exterior_window=window_exterior.get(room["id"], False),
                egress_reachable=room["id"] in reachable,
            )
        )

    model = GeometryModel(
        rooms=rooms,
        doors=doors,
        ceiling_height_mm=min(heights) if heights else 2700,
    )
    model.room_by_id = {r.id: r for r in rooms}
    return model


def _bfs_reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    seen = {start}
    q = deque([start])
    while q:
        node = q.popleft()
        for nbr in graph.get(node, set()):
            if nbr not in seen:
                seen.add(nbr)
                q.append(nbr)
    return seen


# --- metric registry -------------------------------------------------------
RoomMetricFn = Callable[[RoomMetrics, GeometryModel], float]
DoorMetricFn = Callable[[DoorMetrics, GeometryModel], float]

ROOM_METRICS: dict[str, RoomMetricFn] = {
    "room.area_mm2": lambda r, m: float(r.area_mm2),
    "room.min_dimension_mm": lambda r, m: float(r.width_mm),
    "room.aspect_ratio": lambda r, m: (r.depth_mm / r.width_mm) if r.width_mm else 0.0,
    "room.window_area_ratio": lambda r, m: (r.window_area_mm2 / r.area_mm2) if r.area_mm2 else 0.0,
    "room.ceiling_height_mm": lambda r, m: float(m.ceiling_height_mm),
    "egress.reachable": lambda r, m: 1.0 if r.egress_reachable else 0.0,
}

DOOR_METRICS: dict[str, DoorMetricFn] = {
    "door.clear_width_mm": lambda d, m: float(d.width_mm),
}
