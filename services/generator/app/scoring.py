"""Deterministic scoring used to rank candidate layouts (a lightweight stand-in until the full
Phase-09 validator scores plans). Pure functions over Plan + ProgramGraph dicts."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from . import geometry as geom

POSITIVE_RELATIONS = {"adjacent", "connected_door", "connected_open", "near"}
DEFAULT_EDGE_WEIGHT = 50


def edge_weight(e: dict[str, Any]) -> float:
    """Adjacency strength on a 0-1 scale, from the 0-100 `weight` field (default 50)."""
    w = e.get("weight")
    if w is None:
        w = DEFAULT_EDGE_WEIGHT
    return max(0.0, min(100.0, float(w))) / 100.0


def rooms_touch(a_poly: Sequence[Sequence[float]], b_poly: Sequence[Sequence[float]], tol: int = 2) -> bool:
    """True if two room polygons share a wall segment (collinear, overlapping). Works for any
    shape, not just axis-aligned rectangles."""
    pa = geom.to_poly(a_poly)
    pb = geom.to_poly(b_poly)
    ea = geom.edges(pa)
    eb = geom.edges(pb)
    for sega in ea:
        for segb in eb:
            sh = geom.shared_segment(sega, segb, tol=float(tol))
            if sh and sh[0] > tol:
                return True
    return False


def area_fit(plan: dict[str, Any], program: dict[str, Any]) -> float:
    targets = {n["id"]: n.get("area_target_mm2") for n in program.get("nodes", [])}
    ratios: list[float] = []
    for level in plan["levels"]:
        for room in level["rooms"]:
            target = targets.get(room.get("program_node_id"))
            if target and room["area_mm2"] > 0:
                ratios.append(min(room["area_mm2"] / target, target / room["area_mm2"]))
    return sum(ratios) / len(ratios) if ratios else 1.0


def adjacency_satisfaction(plan: dict[str, Any], program: dict[str, Any]) -> float:
    edges = [e for e in program.get("edges", []) if e["relation"] in POSITIVE_RELATIONS]
    if not edges:
        return 1.0
    # map program node id -> room polygon
    poly: dict[str, list[list[int]]] = {}
    for level in plan["levels"]:
        for room in level["rooms"]:
            nid = room.get("program_node_id")
            if nid:
                poly[nid] = room["polygon"]["rings"][0]["points"]
    satisfied_weight = 0.0
    total_weight = 0.0
    for e in edges:
        w = edge_weight(e)
        total_weight += w
        pa = _node_polys(poly, e["a"])
        pb = _node_polys(poly, e["b"])
        if any(rooms_touch(a, b) for a in pa for b in pb):
            satisfied_weight += w
    return satisfied_weight / total_weight if total_weight > 0 else 1.0


def _node_polys(poly: dict[str, list[list[int]]], node_id: str) -> list[list[list[int]]]:
    """Return polygons for a program node, accounting for quantity-expanded ids (id-1, id-2, …)."""
    out = []
    if node_id in poly:
        out.append(poly[node_id])
    out.extend(v for k, v in poly.items() if k.startswith(f"{node_id}-"))
    return out


def score_plan(plan: dict[str, Any], program: dict[str, Any]) -> tuple[float, dict[str, float]]:
    adj = adjacency_satisfaction(plan, program)
    fit = area_fit(plan, program)
    overall = 100.0 * (0.6 * adj + 0.4 * fit)
    return round(overall, 1), {"adjacency": round(adj * 100, 1), "area_fit": round(fit * 100, 1)}
