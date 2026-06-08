"""Evaluate a RuleSet against a Plan -> ValidationReport. Pure + deterministic."""

from __future__ import annotations

from typing import Any

from .metrics import DOOR_METRICS, ROOM_METRICS, GeometryModel, RoomMetrics, build_model

_COMPARATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
}

_SEVERITY_WEIGHT = {"error": 3.0, "warning": 1.0, "info": 0.5}


def _scope(rule: dict[str, Any]) -> str:
    metric = str(rule.get("predicate", {}).get("metric", ""))
    applies = rule.get("applies_to") or {}
    element = applies.get("element")
    if element == "door" or metric.startswith("door."):
        return "door"
    return "room"


def _rooms_in_scope(model: GeometryModel, rule: dict[str, Any]) -> list[RoomMetrics]:
    types = (rule.get("applies_to") or {}).get("room_types")
    if not types:
        return model.rooms
    allowed = set(types)
    return [r for r in model.rooms if r.type in allowed]


def _eval_cmp(value: float, comparator: str, threshold: float) -> bool:
    fn = _COMPARATORS.get(comparator)
    return bool(fn(value, threshold)) if fn else False


def evaluate_rule(model: GeometryModel, rule: dict[str, Any]) -> dict[str, Any]:
    pred = rule.get("predicate", {})
    if pred.get("op") != "cmp":
        return {"rule_id": rule["id"], "status": "na", "severity": rule["severity"],
                "message": "unsupported predicate"}

    metric = pred["metric"]
    comparator = pred["comparator"]
    threshold = float(pred["value"])
    scope = _scope(rule)

    failures: list[tuple[str, float]] = []
    evaluated = 0

    if scope == "door":
        fn = DOOR_METRICS.get(metric)
        for d in model.doors:
            if fn is None:
                continue
            evaluated += 1
            if not _eval_cmp(fn(d, model), comparator, threshold):
                failures.append((d.id, fn(d, model)))
    else:
        fn_r = ROOM_METRICS.get(metric)
        for r in _rooms_in_scope(model, rule):
            if fn_r is None:
                continue
            evaluated += 1
            if not _eval_cmp(fn_r(r, model), comparator, threshold):
                failures.append((r.id, fn_r(r, model)))

    citation = rule.get("citation", {})
    if evaluated == 0:
        return {"rule_id": rule["id"], "status": "na", "severity": rule["severity"]}
    if not failures:
        return {"rule_id": rule["id"], "status": "pass", "severity": rule["severity"]}

    bad_id, bad_val = failures[0]
    return {
        "rule_id": rule["id"],
        "status": "fail",
        "severity": rule["severity"],
        "geometry_ref": bad_id,
        "message": (
            f"{bad_id}: {metric}={_fmt(bad_val)} fails {comparator} {_fmt(threshold)} "
            f"({citation.get('doc', '')} §{citation.get('section', '')})"
        ),
        "fix_hint": _fix_hint(metric, comparator, threshold),
    }


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}"


def _fix_hint(metric: str, comparator: str, threshold: float) -> str:
    direction = "increase" if comparator in (">=", ">") else "decrease"
    return f"{direction} {metric} to satisfy {comparator} {_fmt(threshold)}"


def validate(plan: dict[str, Any], ruleset: dict[str, Any]) -> dict[str, Any]:
    model = build_model(plan)
    results = [evaluate_rule(model, rule) for rule in ruleset.get("rules", [])]

    by_cat: dict[str, list[tuple[float, bool]]] = {}
    total_w = 0.0
    passed_w = 0.0
    rule_cat = {r["id"]: r.get("category", "other") for r in ruleset.get("rules", [])}
    for res in results:
        if res["status"] == "na":
            continue
        w = _SEVERITY_WEIGHT.get(res["severity"], 1.0)
        ok = res["status"] == "pass"
        total_w += w
        passed_w += w if ok else 0.0
        by_cat.setdefault(rule_cat.get(res["rule_id"], "other"), []).append((w, ok))

    score = round(100.0 * passed_w / total_w, 1) if total_w else 100.0
    category_scores = {
        cat: round(100.0 * sum(w for w, ok in items if ok) / sum(w for w, _ in items), 1)
        for cat, items in by_cat.items()
        if sum(w for w, _ in items) > 0
    }

    return {
        "schema_version": 1,
        "plan_id": plan["id"],
        "ruleset_id": ruleset["id"],
        "score": score,
        "category_scores": category_scores,
        "results": results,
    }
