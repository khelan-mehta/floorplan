"""Deterministic layout solver: Boundary + ProgramGraph -> candidate Plan documents.

Method: order rooms by adjacency proximity, then **partition the actual boundary polygon** by target
areas with a recursive area-bisection (see ``partition.py``). Every room therefore stays inside the
true outline, so concave / L-shaped / arc-approximated (many-vertex) boundaries are supported — not
just the bounding box. Walls are the room-polygon edges (exterior where they lie on the outline);
doors connect rooms that share an edge, with a circulation spanning tree from the entry guaranteeing
egress; exterior doors and windows go on exterior edges. Reproducible by ``seed``.
"""

from __future__ import annotations

import math
import random
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from . import geometry as geom
from .partition import partition_polygon
from .scoring import POSITIVE_RELATIONS, score_plan

DEFAULT_HEIGHT = 2700
MIN_SHARE_MM = 1000  # minimum shared-edge length to place an interior door
WIN_H_MM = 1200  # window height
WIN_SILL_MM = 900
DEFAULT_WIN_W_MM = 1500
CODE_DAYLIGHT_RATIO = 0.08  # window area / floor area (the validator's daylight rule, §1204.2)
# Score an exterior edge's midpoint so the preferred facade wins (higher = better).
SIDE_PICK: dict[str, Callable[[tuple[float, float]], float]] = {
    "north": lambda m: m[1],
    "south": lambda m: -m[1],
    "east": lambda m: m[0],
    "west": lambda m: -m[0],
}
ENTRY_TYPES = ("entry", "foyer", "mudroom", "lobby", "vestibule", "reception")
PUBLIC_TYPES = ("living", "hall", "hallway", "corridor", "dining", "lobby")
SECONDARY_DOOR_TYPES = ("garage", "kitchen", "utility", "laundry", "mudroom", "balcony", "storage")
# Rooms that need daylight/ventilation (the code applies its window rules to these) -> exterior.
HABITABLE_TYPES = frozenset(
    {"living", "dining", "kitchen", "bedroom", "master_bedroom", "office", "study", "family", "den",
     "guest", "nursery", "playroom", "meeting", "reception"}
)
# Rooms that can sit interior without daylight -> good candidates to trade an interior habitable room.
SERVICE_TYPES = frozenset(
    {"corridor", "hallway", "hall", "bathroom", "ensuite", "wc", "closet", "storage", "store",
     "laundry", "utility", "mechanical", "garage", "pantry", "mudroom", "stair", "elevator"}
)
MIN_HABITABLE_AREA = {"bedroom": 7_000_000, "master_bedroom": 7_000_000, "kitchen": 4_600_000}
MIN_DOOR_MM = 815  # code minimum clear door width


def expand_nodes(program: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand quantity counts into individual room specs, recording the source program node id."""
    out: list[dict[str, Any]] = []
    for node in program.get("nodes", []):
        count = max(1, int(node.get("count", 1)))
        for i in range(count):
            rid = node["id"] if count == 1 else f"{node['id']}-{i + 1}"
            out.append(
                {
                    "room_id": f"room-{rid}",
                    "program_node_id": node["id"] if count == 1 else f"{node['id']}-{i + 1}",
                    "type": node["type"],
                    "area_target_mm2": node.get("area_target_mm2"),
                    "requires_window": bool(node.get("requires_window")),
                    "windows": node.get("windows"),
                    "window_to_wall_ratio": node.get("window_to_wall_ratio"),
                }
            )
    return out


def _order_by_adjacency(specs: list[dict[str, Any]], program: dict[str, Any]) -> list[dict[str, Any]]:
    """BFS over the adjacency graph so related rooms end up next to each other in the partition."""
    by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in specs:
        by_node[s["program_node_id"]].append(s)
        base = s["program_node_id"].rsplit("-", 1)[0]
        if base != s["program_node_id"]:
            by_node[base].append(s)

    adj: dict[str, set[str]] = defaultdict(set)
    for e in program.get("edges", []):
        if e["relation"] in POSITIVE_RELATIONS:
            adj[e["a"]].add(e["b"])
            adj[e["b"]].add(e["a"])

    seen_specs: set[str] = set()
    ordered: list[dict[str, Any]] = []
    queue = deque(n["id"] for n in program.get("nodes", []))
    visited_nodes: set[str] = set()
    while queue:
        node_id = queue.popleft()
        if node_id in visited_nodes:
            continue
        visited_nodes.add(node_id)
        for s in by_node.get(node_id, []):
            if s["room_id"] not in seen_specs:
                seen_specs.add(s["room_id"])
                ordered.append(s)
        for nbr in sorted(adj.get(node_id, [])):
            if nbr not in visited_nodes:
                queue.append(nbr)
    for s in specs:  # append any not reached via edges
        if s["room_id"] not in seen_specs:
            seen_specs.add(s["room_id"])
            ordered.append(s)
    return ordered


def _matches_node(spec: dict[str, Any], node_id: str) -> bool:
    pid = str(spec["program_node_id"])
    return pid == node_id or pid.startswith(f"{node_id}-")


# --- geometry helpers ------------------------------------------------------------------------


def _exterior_edges(
    poly: geom.Poly, outline_edges: list[tuple[geom.Pt, geom.Pt]]
) -> list[tuple[int, geom.Pt, geom.Pt, float]]:
    """Room edges that lie on the building outline, as (edge_index, a, b, length)."""
    out = []
    for i, (a, b) in enumerate(geom.edges(poly)):
        mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        if geom.point_on_boundary(mid, outline_edges, tol=2.0):
            out.append((i, a, b, geom.edge_len((a, b))))
    return out


def _door(wall_id: str, offset: float, width: float, connects: list[str], kind: str) -> dict[str, Any]:
    return {
        "id": f"d-{connects[0]}-{connects[1]}-{int(offset)}",
        "wall_id": wall_id,
        "kind": "opening" if kind == "connected_open" else "door",
        "offset_mm": int(max(0, offset)),
        "width_mm": int(max(700, width)),
        "height_mm": 2100,
        "connects": connects,
    }


# --- main build ------------------------------------------------------------------------------


def _improve_exterior(
    specs: list[dict[str, Any]],
    rooms: list[dict[str, Any]],
    room_polys: dict[str, geom.Poly],
    outline_edges: list[tuple[geom.Pt, geom.Pt]],
) -> None:
    """Swap interior habitable rooms with exterior service rooms so habitable rooms get daylight."""
    room_by_id = {r["id"]: r for r in rooms}
    type_by = {s["room_id"]: s["type"] for s in specs}
    ids = [s["room_id"] for s in specs if s["room_id"] in room_polys]

    def is_ext(rid: str) -> bool:
        return bool(_exterior_edges(room_polys[rid], outline_edges))

    hab_interior = [r for r in ids if type_by[r] in HABITABLE_TYPES and not is_ext(r)]
    svc_exterior = [r for r in ids if type_by[r] in SERVICE_TYPES and is_ext(r)]

    def apply(rid: str) -> None:
        poly = room_polys[rid]
        room_by_id[rid]["polygon"] = {"rings": [{"points": geom.round_poly(poly)}]}
        room_by_id[rid]["area_mm2"] = round(geom.area(poly))
        room_by_id[rid]["centroid"] = [round(c) for c in geom.centroid(poly)]

    for h in hab_interior:
        need = MIN_HABITABLE_AREA.get(type_by[h], 0)
        cand = next((s for s in svc_exterior if geom.area(room_polys[s]) >= need), None)
        if cand is None:
            continue
        svc_exterior.remove(cand)
        room_polys[h], room_polys[cand] = room_polys[cand], room_polys[h]
        apply(h)
        apply(cand)


def _ensure_entry_exterior(
    entry_spec: dict[str, Any],
    specs: list[dict[str, Any]],
    rooms: list[dict[str, Any]],
    room_polys: dict[str, geom.Poly],
    outline_edges: list[tuple[geom.Pt, geom.Pt]],
) -> None:
    """Guarantee the chosen Main-entry room sits on the building exterior (so the entrance door can
    go there on the requested facade) — the user's 'fix entry' control."""
    node = entry_spec.get("entry_node_id")
    if not node:
        return
    room_by_id = {r["id"]: r for r in rooms}
    type_by = {s["room_id"]: s["type"] for s in specs}
    ids = [s["room_id"] for s in specs if s["room_id"] in room_polys]
    entry_rooms = [r for r in ids if _matches_node(spec_for(specs, r), node)]

    def is_ext(rid: str) -> bool:
        return bool(_exterior_edges(room_polys[rid], outline_edges))

    if not entry_rooms or any(is_ext(r) for r in entry_rooms):
        return
    e = entry_rooms[0]
    cand = next((r for r in ids if r != e and is_ext(r) and type_by[r] in SERVICE_TYPES), None)
    if cand is None:
        cand = next((r for r in ids if r != e and is_ext(r) and type_by[r] not in HABITABLE_TYPES), None)
    if cand is None:
        return
    room_polys[e], room_polys[cand] = room_polys[cand], room_polys[e]
    for rid in (e, cand):
        poly = room_polys[rid]
        room_by_id[rid]["polygon"] = {"rings": [{"points": geom.round_poly(poly)}]}
        room_by_id[rid]["area_mm2"] = round(geom.area(poly))
        room_by_id[rid]["centroid"] = [round(c) for c in geom.centroid(poly)]


def spec_for(specs: list[dict[str, Any]], room_id: str) -> dict[str, Any]:
    return next(s for s in specs if s["room_id"] == room_id)


def _build_plan(boundary: dict[str, Any], program: dict[str, Any], project_id: str, seed: int) -> dict[str, Any]:
    level0 = boundary["levels"][0]
    outline = geom.to_poly(level0["outline"]["rings"][0]["points"])
    outline_edges = geom.edges(outline)
    floor_h = max(2000, int(level0.get("floor_to_floor_mm", 3000)) - 300)
    entry_spec = program.get("entry") or {}

    specs = _order_by_adjacency(expand_nodes(program), program)
    if not specs:
        specs = [{"room_id": "room-1", "program_node_id": "room-1", "type": "living",
                  "area_target_mm2": None, "requires_window": False}]

    rng = random.Random(seed)
    entry_node = entry_spec.get("entry_node_id")
    front = [s for s in specs if entry_node and _matches_node(s, entry_node)]
    if front:
        rest = [s for s in specs if s not in front]
        k = rng.randrange(len(rest) + 1) if rest else 0
        specs = front + rest[k:] + rest[:k]
    elif len(specs) > 1:
        rotation = rng.randrange(len(specs))
        specs = specs[rotation:] + specs[:rotation]

    avg = geom.area(outline) / max(1, len(specs))
    weights = [float(s["area_target_mm2"] or avg) for s in specs]
    # Snap partition cuts to the building's own lines (outline vertices) so rooms align to notches.
    snaps_x = [p[0] for p in outline]
    snaps_y = [p[1] for p in outline]
    polys = partition_polygon(weights, outline, snaps_x, snaps_y)

    rooms: list[dict[str, Any]] = []
    room_polys: dict[str, geom.Poly] = {}
    for spec, poly in zip(specs, polys, strict=True):
        ring = geom.round_poly(poly)
        if len(ring) < 3:  # a sliver collapsed on rounding — skip (rare; keeps geometry valid)
            continue
        fp = geom.to_poly(ring)
        room_polys[spec["room_id"]] = fp
        rooms.append(
            {
                "id": spec["room_id"],
                "program_node_id": spec["program_node_id"],
                "type": spec["type"],
                "polygon": {"rings": [{"points": ring}]},
                "area_mm2": round(geom.area(fp)),
                "centroid": [round(c) for c in geom.centroid(fp)],
            }
        )

    # Architectural rule: habitable rooms need daylight, so move any that landed interior onto the
    # perimeter by trading polygons with an exterior service room (when it won't break min areas).
    _improve_exterior(specs, rooms, room_polys, outline_edges)
    _ensure_entry_exterior(entry_spec, specs, rooms, room_polys, outline_edges)

    # Walls: one per room-polygon edge; exterior where the edge lies on the outline.
    walls: list[dict[str, Any]] = []
    for room_id, poly in room_polys.items():
        ext = {i for i, _a, _b, _l in _exterior_edges(poly, outline_edges)}
        for i, (a, b) in enumerate(geom.edges(poly)):
            is_ext = i in ext
            walls.append(
                {
                    "id": f"w-{room_id}-{i}",
                    "a": [round(a[0]), round(a[1])],
                    "b": [round(b[0]), round(b[1])],
                    "thickness_mm": 200 if is_ext else 100,
                    "type": "exterior" if is_ext else "interior",
                    "height_mm": floor_h,
                }
            )

    openings = _openings(specs, room_polys, outline_edges, entry_spec, program, floor_h)

    plan_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"fpg-plan:{project_id}:{seed}"))
    return {
        "schema_version": 1,
        "id": plan_id,
        "project_id": project_id,
        "parent_plan_id": None,
        "seed": seed,
        "source": "generated",
        "levels": [{"index": 0, "rooms": rooms, "walls": walls, "openings": openings, "fixtures": []}],
    }


def _adjacency(
    room_ids: list[str], room_polys: dict[str, geom.Poly]
) -> tuple[dict[str, list[tuple[str, float]]], dict[tuple[str, str], dict[str, Any]]]:
    """Shared-edge graph + per-pair info (edge index + offset on each room's wall)."""
    graph: dict[str, list[tuple[str, float]]] = defaultdict(list)
    pair: dict[tuple[str, str], dict[str, Any]] = {}
    present = [r for r in room_ids if r in room_polys]
    for ai in range(len(present)):
        a = present[ai]
        ea = geom.edges(room_polys[a])
        for b in present[ai + 1 :]:
            eb = geom.edges(room_polys[b])
            best: dict[str, Any] | None = None
            for ia, sega in enumerate(ea):
                for ib, segb in enumerate(eb):
                    sh = geom.shared_segment(sega, segb)
                    if sh and sh[0] >= MIN_SHARE_MM and (best is None or sh[0] > best["ov"]):
                        sh_b = geom.shared_segment(segb, sega)
                        best = {
                            "ov": sh[0], "ia": ia, "lo_a": sh[1],
                            "ib": ib, "lo_b": sh_b[1] if sh_b else sh[1],
                        }
            if best is not None:
                graph[a].append((b, best["ov"]))
                graph[b].append((a, best["ov"]))
                pair[(a, b)] = best
    return graph, pair


def _pair_door(p: str, c: str, pair: dict[tuple[str, str], dict[str, Any]], relation: str) -> dict[str, Any] | None:
    info = pair.get((p, c))
    flip = False
    if info is None:
        info = pair.get((c, p))
        flip = True
    if info is None:
        return None
    ia = info["ib"] if flip else info["ia"]
    lo = info["lo_b"] if flip else info["lo_a"]
    ov = info["ov"]
    width = max(float(MIN_DOOR_MM), min(900.0, ov - 100.0))
    offset = lo + (ov - width) / 2.0
    return _door(f"w-{p}-{ia}", offset, width, [p, c], relation)


def _openings(
    specs: list[dict[str, Any]],
    room_polys: dict[str, geom.Poly],
    outline_edges: list[tuple[geom.Pt, geom.Pt]],
    entry_spec: dict[str, Any],
    program: dict[str, Any],
    wall_height: int,
) -> list[dict[str, Any]]:
    room_ids = [s["room_id"] for s in specs if s["room_id"] in room_polys]
    type_by_room = {s["room_id"]: s["type"] for s in specs}
    spec_by_room = {s["room_id"]: s for s in specs}
    requires_window = {s["room_id"]: s.get("requires_window") for s in specs}
    graph, pair = _adjacency(room_ids, room_polys)

    openings: list[dict[str, Any]] = []
    placed: set[tuple[str, str]] = set()

    # exterior edges per room (sorted longest-first)
    ext_by_room = {
        rid: sorted(_exterior_edges(room_polys[rid], outline_edges), key=lambda e: -e[3])
        for rid in room_ids
    }

    # entry room: must have an exterior edge
    entry_room = _resolve_entry(entry_spec, room_ids, ext_by_room, type_by_room, room_polys)

    # 1) circulation spanning tree from the entry (every room reachable -> egress)
    if entry_room is not None:
        visited = {entry_room}
        queue: deque[str] = deque([entry_room])
        while queue:
            cur = queue.popleft()
            for nbr, _ov in sorted(graph.get(cur, []), key=lambda t: -t[1]):
                if nbr in visited:
                    continue
                visited.add(nbr)
                queue.append(nbr)
                key = (min(cur, nbr), max(cur, nbr))
                d = _pair_door(cur, nbr, pair, "connected_door")
                if d and key not in placed:
                    openings.append(d)
                    placed.add(key)

    # 2) explicit program adjacencies that physically touch (extra doors/openings beyond the tree)
    id_to_rooms: dict[str, list[str]] = defaultdict(list)
    for s in specs:
        if s["room_id"] not in room_polys:
            continue
        id_to_rooms[s["program_node_id"]].append(s["room_id"])
        base = s["program_node_id"].rsplit("-", 1)[0]
        if base != s["program_node_id"]:
            id_to_rooms[base].append(s["room_id"])
    for e in program.get("edges", []):
        if e["relation"] not in POSITIVE_RELATIONS:
            continue
        for a_room in id_to_rooms.get(e["a"], []):
            for b_room in id_to_rooms.get(e["b"], []):
                key = (min(a_room, b_room), max(a_room, b_room))
                if key in placed:
                    continue
                d = _pair_door(a_room, b_room, pair, e["relation"])
                if d:
                    openings.append(d)
                    placed.add(key)

    # 3) exterior door(s)
    ext_door_edge: set[tuple[str, int]] = set()
    n_doors = max(1, min(8, int(entry_spec.get("exterior_doors", 1))))
    if entry_room is not None:
        used = set()
        prefer = entry_spec.get("entry_side")
        ed = _exterior_door(entry_room, ext_by_room[entry_room], prefer)
        if ed:
            openings.append(ed[0])
            ext_door_edge.add((entry_room, ed[1]))
            used.add(entry_room)
        others = [r for r in room_ids if r != entry_room and ext_by_room[r]]
        others.sort(key=lambda r: (0 if type_by_room[r] in SECONDARY_DOOR_TYPES else 1, r))
        for rid in others:
            if len(used) >= n_doors:
                break
            ed = _exterior_door(rid, ext_by_room[rid], None)
            if ed:
                openings.append(ed[0])
                ext_door_edge.add((rid, ed[1]))
                used.add(rid)

    # 4) windows: honour the requested count / window-to-wall ratio, but never below the code
    #    daylight minimum (window area >= 8% of floor area), so inputs can't produce a violation.
    for rid in room_ids:
        spec = spec_by_room.get(rid, {})
        free_ext = [e for e in ext_by_room[rid] if (rid, e[0]) not in ext_door_edge and e[3] >= 1000]
        habitable = type_by_room.get(rid, "") in HABITABLE_TYPES
        wants = (
            habitable
            or bool(requires_window.get(rid))
            or bool(spec.get("windows"))
            or bool(spec.get("window_to_wall_ratio"))
        )
        if not wants or not free_ext:
            continue
        floor_area = geom.area(room_polys[rid])
        ext_wall_area = sum(e[3] for e in free_ext) * wall_height
        wwr = float(spec.get("window_to_wall_ratio") or 0.0)
        design_area = wwr * ext_wall_area
        # Target a margin above the code daylight ratio so integer rounding never drops below it.
        code_area = (CODE_DAYLIGHT_RATIO + 0.02) * floor_area if (habitable or requires_window.get(rid)) else 0.0
        target = max(design_area, code_area)
        if target <= 0:
            continue
        req = int(spec.get("windows") or 0)
        count = req if req > 0 else max(1, math.ceil(target / (DEFAULT_WIN_W_MM * WIN_H_MM)))
        openings.extend(_place_windows(rid, free_ext, count, target))

    return openings


def _place_windows(
    rid: str,
    free_ext: list[tuple[int, geom.Pt, geom.Pt, float]],
    count: int,
    total_area: float,
) -> list[dict[str, Any]]:
    """Distribute `count` windows over a room's free exterior edges (round-robin, longest first),
    sized so their combined area ~= total_area. Returns window opening dicts."""
    if not free_ext or count <= 0:
        return []
    per_w = max(600.0, (total_area / count) / WIN_H_MM)
    by_edge: dict[int, list[None]] = defaultdict(list)
    edges_sorted = sorted(free_ext, key=lambda e: -e[3])
    for i in range(count):
        by_edge[edges_sorted[i % len(edges_sorted)][0]].append(None)
    edge_len = {e[0]: e[3] for e in free_ext}
    out: list[dict[str, Any]] = []
    for edge_idx, wins in by_edge.items():
        m = len(wins)
        slot = edge_len[edge_idx] / m
        w = max(600.0, min(per_w, slot - 400.0, edge_len[edge_idx] - 400.0))
        if w < 600:
            continue
        for j in range(m):
            center = (j + 0.5) * slot
            out.append(
                {
                    "id": f"win-{rid}-{edge_idx}-{j}",
                    "wall_id": f"w-{rid}-{edge_idx}",
                    "kind": "window",
                    "offset_mm": int(max(0.0, center - w / 2.0)),
                    "width_mm": int(w),
                    "height_mm": WIN_H_MM,
                    "sill_mm": WIN_SILL_MM,
                    "connects": [rid, "exterior"],
                }
            )
    return out


def _resolve_entry(
    entry_spec: dict[str, Any],
    room_ids: list[str],
    ext_by_room: dict[str, list[tuple[int, geom.Pt, geom.Pt, float]]],
    type_by_room: dict[str, str],
    room_polys: dict[str, geom.Poly],
) -> str | None:
    exterior = [r for r in room_ids if ext_by_room.get(r)]
    if not exterior:
        return None
    node = entry_spec.get("entry_node_id")
    if node:
        named = [r for r in exterior if r == f"room-{node}" or r.startswith(f"room-{node}-")]
        if named:
            return sorted(named, key=lambda r: (geom.area(room_polys[r]), r))[0]

    def rank(r: str) -> int:
        t = type_by_room[r]
        return 0 if t in ENTRY_TYPES else 1 if t in PUBLIC_TYPES else 2

    return sorted(exterior, key=lambda r: (rank(r), geom.area(room_polys[r]), r))[0]


def _exterior_door(
    room_id: str,
    ext_edges: list[tuple[int, geom.Pt, geom.Pt, float]],
    side: str | None,
) -> tuple[dict[str, Any], int] | None:
    usable = [e for e in ext_edges if e[3] >= 1100]
    if not usable:
        return None
    if side is not None and side in SIDE_PICK:
        keyfn = SIDE_PICK[side]
        pick = max(usable, key=lambda e: keyfn(((e[1][0] + e[2][0]) / 2, (e[1][1] + e[2][1]) / 2)))
    else:
        pick = usable[0]  # longest (ext_edges sorted desc)
    i, _a, _b, length = pick
    width = max(float(MIN_DOOR_MM), min(1000.0, length - 200.0))
    door = {
        "id": f"d-ext-{room_id}",
        "wall_id": f"w-{room_id}-{i}",
        "kind": "door",
        "offset_mm": int((length - width) / 2.0),
        "width_mm": int(width),
        "height_mm": 2100,
        "connects": [room_id, "exterior"],
    }
    return door, i


def generate_layouts(
    boundary: dict[str, Any],
    program: dict[str, Any],
    *,
    count: int = 4,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Produce up to `count` distinct, scored candidate plans."""
    project_id = program.get("project_id") or program.get("id") or "fpg-unknown"
    seen: set[tuple[tuple[int, int], ...]] = set()
    candidates: list[tuple[float, dict[str, Any]]] = []
    for i in range(count * 3):
        plan = _build_plan(boundary, program, project_id, seed + i)
        signature = tuple(
            sorted((r["centroid"][0] // 500, r["centroid"][1] // 500) for r in plan["levels"][0]["rooms"])
        )
        if signature in seen:
            continue
        seen.add(signature)
        score, _breakdown = score_plan(plan, program)
        plan["score"] = score
        candidates.append((score, plan))
        if len(candidates) >= count:
            break
    candidates.sort(key=lambda c: c[0], reverse=True)
    return [p for _s, p in candidates]
