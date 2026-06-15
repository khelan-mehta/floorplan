"""AI critic: turn free-text feedback about a plan ("kitchen too small", "bedroom should be
near the bathroom") into structured ProgramGraph adjustments, which are then fed back through
the generator for a new plan version. Mirrors the OpenAI function-calling pattern used in
`services/codes/app/extract.py`, with a deterministic keyword-based fallback when no
`OPENAI_API_KEY` is configured (or the call fails)."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from .settings import settings

_VALID_RELATIONS = {"adjacent", "connected_door", "connected_open", "near", "not_adjacent"}

_ADJUSTMENTS_PARAMETERS = {
    "type": "object",
    "properties": {
        "node_adjustments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "area_delta_pct": {"type": "number", "minimum": -50, "maximum": 100},
                    "requires_window": {"type": "boolean"},
                    "windows": {"type": "integer", "minimum": 0},
                },
                "required": ["id"],
            },
        },
        "edge_adjustments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "a": {"type": "string"},
                    "b": {"type": "string"},
                    "relation": {"type": "string", "enum": sorted(_VALID_RELATIONS)},
                    "weight": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["a", "b"],
            },
        },
        "notes": {"type": "string", "description": "Human-readable summary of what changed."},
    },
    "required": ["notes"],
}

_ADJUSTMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "propose_adjustments",
        "description": (
            "Propose the minimal ProgramGraph adjustments (room target areas, window "
            "requirements, and adjacency relations/weights) that address the user's feedback "
            "about a generated floor plan."
        ),
        "parameters": _ADJUSTMENTS_PARAMETERS,
    },
}

_SYSTEM = (
    "You are an architectural-programming assistant. Given a floor plan's room program (nodes: "
    "id/type/label/area_target_mm2/requires_window/windows, and adjacency edges: a/b/relation/"
    "weight where weight is 0-100 and higher means the two rooms should be placed closer "
    "together) and a user's free-text complaint about the generated plan, propose the smallest "
    "set of program adjustments that would address it: resize rooms via area_delta_pct "
    "(percent change, -50..100), add/raise window requirements, or add/adjust adjacency edges "
    "(relation + weight). Only reference node ids that exist in the program. Always include a "
    "short `notes` summary of what you changed and why."
)


def _summarize_program(program: dict[str, Any]) -> str:
    nodes = [
        {
            "id": n["id"],
            "type": n.get("type"),
            "label": n.get("label"),
            "area_target_mm2": n.get("area_target_mm2"),
            "requires_window": n.get("requires_window", False),
            "windows": n.get("windows"),
        }
        for n in program.get("nodes", [])
    ]
    edges = [
        {"a": e["a"], "b": e["b"], "relation": e["relation"], "weight": e.get("weight", 50)}
        for e in program.get("edges", [])
    ]
    return json.dumps({"nodes": nodes, "edges": edges})


def propose_adjustments(feedback: str, program: dict[str, Any]) -> dict[str, Any]:
    """Return `{"node_adjustments": [...], "edge_adjustments": [...], "notes": str}`."""
    if settings.openai_api_key:
        try:
            return _propose_with_openai(feedback, program)
        except Exception:  # pragma: no cover - network/SDK issues fall back deterministically
            pass
    return _propose_deterministic(feedback, program)


def _propose_with_openai(feedback: str, program: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
    from openai import OpenAI  # type: ignore[import-not-found]

    kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**kwargs)

    resp = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": f"Program: {_summarize_program(program)}\n\nFeedback: {feedback}",
            },
        ],
        tools=[_ADJUSTMENTS_TOOL],
        tool_choice={"type": "function", "function": {"name": "propose_adjustments"}},
    )
    data = _first_tool_args(resp)
    if not data:
        return _propose_deterministic(feedback, program)
    return _sanitize(data, program)


def _first_tool_args(resp: Any) -> dict[str, Any] | None:  # pragma: no cover
    choices = getattr(resp, "choices", None)
    if not choices:
        return None
    tool_calls = getattr(choices[0].message, "tool_calls", None)
    if not tool_calls:
        return None
    args = tool_calls[0].function.arguments
    return json.loads(args) if isinstance(args, str) else dict(args)


def _sanitize(data: dict[str, Any], program: dict[str, Any]) -> dict[str, Any]:
    """Drop adjustments that reference unknown node ids or invalid relations."""
    node_ids = {n["id"] for n in program.get("nodes", [])}
    node_adjustments = [
        n for n in data.get("node_adjustments", []) if isinstance(n, dict) and n.get("id") in node_ids
    ]
    edge_adjustments = [
        e
        for e in data.get("edge_adjustments", [])
        if isinstance(e, dict)
        and e.get("a") in node_ids
        and e.get("b") in node_ids
        and e.get("relation", "adjacent") in _VALID_RELATIONS
    ]
    return {
        "node_adjustments": node_adjustments,
        "edge_adjustments": edge_adjustments,
        "notes": str(data.get("notes", "")),
    }


# --- deterministic fallback -------------------------------------------------------------------

_BIGGER_WORDS = ("bigger", "larger", "more space", "too small", "too cramped", "expand", "enlarge")
_SMALLER_WORDS = ("smaller", "too big", "too large", "shrink", "reduce")
_NEAR_WORDS = ("near", "close to", "next to", "closer to", "adjacent to", "beside")
_WINDOW_WORDS = ("window", "light", "daylight", "sunlight", "natural light")


_STOPWORDS = {
    "the", "a", "an", "to", "of", "is", "in", "on", "near", "next", "by", "and", "or",
    "room", "area", "space",
}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWORDS}


def _matching_nodes(feedback_lower: str, program: dict[str, Any]) -> list[dict[str, Any]]:
    feedback_tokens = _tokens(feedback_lower)
    matches = []
    for n in program.get("nodes", []):
        names = {n["id"], str(n.get("type", "")), str(n.get("label", ""))}
        node_tokens: set[str] = set()
        for name in names:
            node_tokens |= _tokens(re.sub(r"[-_]", " ", name))
        if node_tokens & feedback_tokens:
            matches.append(n)
    return matches


def _propose_deterministic(feedback: str, program: dict[str, Any]) -> dict[str, Any]:
    text = feedback.lower()
    matches = _matching_nodes(text, program)
    node_adjustments: list[dict[str, Any]] = []
    edge_adjustments: list[dict[str, Any]] = []
    notes: list[str] = []

    if any(w in text for w in _BIGGER_WORDS):
        for n in matches:
            node_adjustments.append({"id": n["id"], "area_delta_pct": 20})
            notes.append(f"increased target area of '{n.get('label', n['id'])}' by 20%")
    elif any(w in text for w in _SMALLER_WORDS):
        for n in matches:
            node_adjustments.append({"id": n["id"], "area_delta_pct": -20})
            notes.append(f"reduced target area of '{n.get('label', n['id'])}' by 20%")

    if any(w in text for w in _WINDOW_WORDS):
        for n in matches:
            node_adjustments.append({"id": n["id"], "requires_window": True})
            notes.append(f"added a window requirement to '{n.get('label', n['id'])}'")

    if any(w in text for w in _NEAR_WORDS) and len(matches) >= 2:
        a, b = matches[0], matches[1]
        edge_adjustments.append({"a": a["id"], "b": b["id"], "relation": "adjacent", "weight": 90})
        notes.append(f"raised the adjacency between '{a['id']}' and '{b['id']}' to 90")

    if not notes:
        notes.append("No matching rooms found in the feedback; no adjustments made.")

    return {
        "node_adjustments": node_adjustments,
        "edge_adjustments": edge_adjustments,
        "notes": "; ".join(notes),
    }


# --- applying adjustments ----------------------------------------------------------------------


def apply_adjustments(program: dict[str, Any], adjustments: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of `program` with the proposed adjustments applied."""
    out = copy.deepcopy(program)
    nodes_by_id = {n["id"]: n for n in out.get("nodes", [])}

    for adj in adjustments.get("node_adjustments", []):
        node = nodes_by_id.get(adj.get("id"))
        if not node:
            continue
        delta = adj.get("area_delta_pct")
        if delta is not None and node.get("area_target_mm2"):
            factor = 1.0 + float(delta) / 100.0
            node["area_target_mm2"] = max(1, round(node["area_target_mm2"] * factor))
        if "requires_window" in adj:
            node["requires_window"] = bool(adj["requires_window"])
        if "windows" in adj:
            node["windows"] = int(adj["windows"])

    edges = out.setdefault("edges", [])
    for adj in adjustments.get("edge_adjustments", []):
        a, b = adj.get("a"), adj.get("b")
        existing = next(
            (e for e in edges if {e["a"], e["b"]} == {a, b}),
            None,
        )
        if existing:
            if "relation" in adj:
                existing["relation"] = adj["relation"]
            if "weight" in adj:
                existing["weight"] = adj["weight"]
        else:
            edges.append(
                {
                    "a": a,
                    "b": b,
                    "relation": adj.get("relation", "adjacent"),
                    "weight": adj.get("weight", 70),
                }
            )

    return out
