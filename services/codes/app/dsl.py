"""The shared rule-predicate DSL (mirrors the validator's metric registry, Phase 09).

A `Rule.predicate` is a small, safe AST. The codes service only emits the `cmp` form
(`{op, metric, comparator, value}`); the validator (Phase 09) is the canonical interpreter.
Keeping the metric registry here lets extraction validate that a predicate is well-formed and
flag references to metrics the validator does not (yet) implement.
"""

from __future__ import annotations

from typing import Any

# Metrics the validator (services/validator/app/metrics.py) can currently evaluate.
EXECUTABLE_METRICS: frozenset[str] = frozenset(
    {
        "room.area_mm2",
        "room.min_dimension_mm",
        "room.aspect_ratio",
        "room.window_area_ratio",
        "room.ceiling_height_mm",
        "egress.reachable",
        "door.clear_width_mm",
    }
)

# Additional metrics defined in the DSL/registry but not yet derivable from current plan geometry
# (the validator returns `na` for these until the geometry model grows). Still valid predicates.
KNOWN_METRICS: frozenset[str] = EXECUTABLE_METRICS | frozenset(
    {
        "corridor.min_width_mm",
        "stair.run_mm",
        "stair.rise_mm",
        "window.area_ratio",
        "egress.travel_distance_mm",
        "building.coverage_ratio",
        "building.far",
    }
)

COMPARATORS: frozenset[str] = frozenset({">=", "<=", "==", "<", ">"})


def validate_predicate(pred: dict[str, Any]) -> tuple[bool, str]:
    """Return (ok, reason). A predicate is well-formed if it is a `cmp` over a known metric."""
    if pred.get("op") != "cmp":
        return False, f"unsupported op: {pred.get('op')!r}"
    metric = pred.get("metric")
    if metric not in KNOWN_METRICS:
        return False, f"unknown metric: {metric!r}"
    if pred.get("comparator") not in COMPARATORS:
        return False, f"unknown comparator: {pred.get('comparator')!r}"
    if not isinstance(pred.get("value"), (int, float)):
        return False, "value must be numeric"
    return True, "ok"


def is_executable(pred: dict[str, Any]) -> bool:
    """True if the validator can actually evaluate this predicate against plan geometry today."""
    return pred.get("op") == "cmp" and pred.get("metric") in EXECUTABLE_METRICS
