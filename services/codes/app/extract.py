"""Prose clause -> structured ``Rule`` extraction.

Two paths produce the same shape:
- **OpenAI** (when ``OPENAI_API_KEY`` is set): each clause chunk is sent to the OpenAI API with a
  strict function/tool JSON schema; the model returns a Rule predicate in the DSL plus a confidence.
  (Optional dependency: ``pip install '.[extract]'``.)
- **Deterministic fallback** (default, offline): a curated template per known clause section maps the
  clause to a Rule predicate. Citations (verbatim text) are taken from the parsed chunk so they trace
  back to the source. This keeps the seed jurisdiction reproducible without an API key.

Either way, the predicate is validated against the shared DSL and a **confidence** is attached.
Low-confidence extractions are flagged and excluded from a published RuleSet until a human approves.
Extraction is decision-support, never an authoritative compliance determination.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .dsl import is_executable, validate_predicate
from .ingest import Chunk
from .settings import settings

# Confidence at/under this is "flagged": excluded from auto-publish until reviewed.
CONFIDENCE_FLAG_THRESHOLD = 0.7


def _to_value(raw: str, kind: str) -> float:
    """Convert a number parsed from clause prose into the predicate's units."""
    n = float(raw)
    if kind == "m2":  # square metres -> square millimetres
        return round(n * 1_000_000)
    if kind == "percent":  # "8 percent" -> 0.08 ratio
        return round(n / 100.0, 4)
    if kind == "mm":
        return round(n)
    return n  # bare ratio


@dataclass
class RuleTemplate:
    """A curated mapping from a clause section to a Rule predicate (deterministic extractor).

    ``value_re`` (searched in the matched clause text) lets the threshold be read from the prose so
    that an amended clause flows into the predicate and produces a reviewable diff on re-ingest.
    When it does not match, the template ``predicate['value']`` is the fallback.
    """

    id: str
    category: str
    section: str
    applies_to: dict[str, Any]
    predicate: dict[str, Any]
    severity: str
    confidence: float = 0.95
    value_re: str | None = None
    value_kind: str = "mm"

    def predicate_from(self, text: str) -> dict[str, Any]:
        pred = dict(self.predicate)
        if self.value_re:
            m = re.search(self.value_re, text)
            if m:
                pred["value"] = _to_value(m.group(1), self.value_kind)
        return pred


@dataclass
class ExtractedRule:
    rule: dict[str, Any]
    confidence: float
    source_chunk_id: str
    source_text: str
    review_status: str = "pending"  # pending | approved | rejected
    notes: str = ""


# Curated templates for the seed jurisdiction. These mirror examples/ruleset-generic-ibc.example.json
# (the canonical expected output); citations are filled from the parsed clause text at extraction time.
SEED_TEMPLATES: dict[str, list[RuleTemplate]] = {
    "generic-ibc-2021": [
        RuleTemplate(
            "min-area-bedroom", "min_area", "1208.1",
            {"room_types": ["bedroom", "master_bedroom"], "element": "room"},
            {"op": "cmp", "metric": "room.area_mm2", "comparator": ">=", "value": 7000000}, "error",
            value_re=r"bedroom\) with a floor area of not less than (\d+(?:\.\d+)?)",
            value_kind="m2",
        ),
        RuleTemplate(
            "min-area-kitchen", "min_area", "1208.1",
            {"room_types": ["kitchen"], "element": "room"},
            {"op": "cmp", "metric": "room.area_mm2", "comparator": ">=", "value": 4600000},
            "warning",
            value_re=r"Kitchens shall have a floor area of not less than (\d+(?:\.\d+)?)",
            value_kind="m2",
        ),
        RuleTemplate(
            "min-dimension-habitable", "min_dimension", "1208.1",
            {"room_types": ["bedroom", "master_bedroom", "living", "dining", "office"],
             "element": "room"},
            {"op": "cmp", "metric": "room.min_dimension_mm", "comparator": ">=", "value": 2100},
            "error",
            value_re=r"less than (\d+) mm in any horizontal",
        ),
        RuleTemplate(
            "min-ceiling-height", "ceiling_height", "1208.2",
            {"element": "room"},
            {"op": "cmp", "metric": "room.ceiling_height_mm", "comparator": ">=", "value": 2300},
            "error",
            value_re=r"not less than (\d+) mm",
        ),
        RuleTemplate(
            "natural-light", "daylight", "1204.2",
            {"room_types": ["bedroom", "master_bedroom", "living", "dining", "office", "kitchen"],
             "element": "room"},
            {"op": "cmp", "metric": "room.window_area_ratio", "comparator": ">=", "value": 0.08},
            "warning",
            value_re=r"not less than (\d+) percent", value_kind="percent",
        ),
        RuleTemplate(
            "natural-ventilation", "ventilation", "1204.4",
            {"room_types": ["bedroom", "master_bedroom", "living", "dining", "kitchen"],
             "element": "room"},
            {"op": "cmp", "metric": "room.window_area_ratio", "comparator": ">=", "value": 0.04},
            "warning",
            value_re=r"not less than (\d+) percent", value_kind="percent",
        ),
        RuleTemplate(
            "room-proportion", "proportion", "1207.3",
            {"room_types": ["bedroom", "master_bedroom", "living", "dining", "office"],
             "element": "room"},
            {"op": "cmp", "metric": "room.aspect_ratio", "comparator": "<=", "value": 3.0}, "info",
            value_re=r"should not exceed (\d+) to 1", value_kind="ratio",
        ),
        RuleTemplate(
            "door-clear-width", "door_width", "1010.1.1",
            {"element": "door"},
            {"op": "cmp", "metric": "door.clear_width_mm", "comparator": ">=", "value": 815},
            "error",
            value_re=r"not less than (\d+) mm",
        ),
        RuleTemplate(
            "egress-reachable", "egress", "1006.2",
            {"element": "room"},
            {"op": "cmp", "metric": "egress.reachable", "comparator": "==", "value": 1}, "error",
        ),
        RuleTemplate(
            "accessible-bathroom-clearance", "accessibility", "1109.2",
            {"room_types": ["bathroom", "wc"], "element": "room"},
            {"op": "cmp", "metric": "room.min_dimension_mm", "comparator": ">=", "value": 1500},
            "warning",
            value_re=r"not less than (\d+) mm",
        ),
        RuleTemplate(
            "corridor-min-width", "corridor_width", "1020.2",
            {"element": "corridor"},
            {"op": "cmp", "metric": "corridor.min_width_mm", "comparator": ">=", "value": 915},
            "error",
            value_re=r"not less than (\d+) mm",
        ),
        RuleTemplate(
            "stair-tread-run", "stair_geometry", "1011.5.2",
            {"element": "stair"},
            {"op": "cmp", "metric": "stair.run_mm", "comparator": ">=", "value": 280}, "error",
            value_re=r"run\) shall be not less than (\d+) mm",
        ),
        # Zoning/coverage is genuinely ambiguous (zoning vs building code) -> low confidence, flagged.
        RuleTemplate(
            "building-coverage", "zoning_coverage", "Z-3.1",
            {"element": "building"},
            {"op": "cmp", "metric": "building.coverage_ratio", "comparator": "<=", "value": 0.6},
            "warning", confidence=0.55,
            value_re=r"more than (\d+) percent", value_kind="percent",
        ),
    ]
}


@dataclass
class ExtractionResult:
    rules: list[ExtractedRule] = field(default_factory=list)
    method: str = "deterministic"


def _build_rule(tmpl: RuleTemplate, chunk: Chunk | None) -> dict[str, Any]:
    citation = (
        chunk.citation()
        if chunk is not None
        else {"doc": "", "section": tmpl.section, "text": ""}
    )
    predicate = tmpl.predicate_from(chunk.text) if chunk is not None else dict(tmpl.predicate)
    return {
        "id": tmpl.id,
        "category": tmpl.category,
        "applies_to": tmpl.applies_to,
        "predicate": predicate,
        "severity": tmpl.severity,
        "citation": citation,
    }


def extract_deterministic(jurisdiction_id: str, chunks: list[Chunk]) -> ExtractionResult:
    by_section = {c.section: c for c in chunks}
    out = ExtractionResult(method="deterministic")
    for tmpl in SEED_TEMPLATES.get(jurisdiction_id, []):
        chunk = by_section.get(tmpl.section)
        ok, reason = validate_predicate(tmpl.predicate)
        if not ok:  # pragma: no cover - guards authoring mistakes
            raise ValueError(f"template {tmpl.id}: bad predicate: {reason}")
        confidence = tmpl.confidence
        if chunk is None:
            confidence = min(confidence, 0.4)  # no source clause found -> low confidence
        rule = _build_rule(tmpl, chunk)
        out.rules.append(
            ExtractedRule(
                rule=rule,
                confidence=round(confidence, 2),
                source_chunk_id=chunk.id if chunk else f"{jurisdiction_id}:{tmpl.section}",
                source_text=chunk.text if chunk else "",
            )
        )
    return out


def extract_rules(jurisdiction_id: str, chunks: list[Chunk]) -> ExtractionResult:
    """Extract rules, preferring the OpenAI API when configured, else the deterministic fallback."""
    if settings.openai_api_key:
        try:
            return _extract_with_openai(jurisdiction_id, chunks)
        except Exception:  # pragma: no cover - network/SDK issues fall back deterministically
            pass
    return extract_deterministic(jurisdiction_id, chunks)


# --- OpenAI extraction (optional) ------------------------------------------------------------

_RULE_PARAMETERS = {
    "type": "object",
    "properties": {
        "applicable": {"type": "boolean",
                       "description": "Does this clause yield a checkable geometric rule?"},
        "category": {"type": "string"},
        "element": {"type": "string",
                    "enum": ["room", "door", "window", "corridor", "stair", "building", "site"]},
        "room_types": {"type": "array", "items": {"type": "string"}},
        "metric": {"type": "string"},
        "comparator": {"type": "string", "enum": [">=", "<=", "==", "<", ">"]},
        "value": {"type": "number"},
        "severity": {"type": "string", "enum": ["error", "warning", "info"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["applicable"],
}

_RULE_TOOL = {
    "type": "function",
    "function": {
        "name": "emit_rule",
        "description": "Emit a machine-checkable building-code rule extracted from one clause.",
        "parameters": _RULE_PARAMETERS,
    },
}

_SYSTEM = (
    "You convert building-code clauses into machine-checkable rules for a floor-plan validator. "
    "Use ONLY these metrics: room.area_mm2 (mm^2), room.min_dimension_mm, room.aspect_ratio, "
    "room.window_area_ratio, room.ceiling_height_mm, egress.reachable (1=true), door.clear_width_mm, "
    "corridor.min_width_mm, stair.run_mm, stair.rise_mm, building.coverage_ratio. Convert all lengths "
    "to millimetres and areas to square millimetres. If the clause is not a checkable geometric "
    "constraint, set applicable=false. Set confidence honestly; flag ambiguity with low confidence."
)


def _extract_with_openai(jurisdiction_id: str, chunks: list[Chunk]) -> ExtractionResult:  # pragma: no cover
    from openai import OpenAI  # type: ignore[import-not-found]

    kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    client = OpenAI(**kwargs)

    out = ExtractionResult(method="openai")
    for chunk in chunks:
        resp = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Clause {chunk.section}: {chunk.text}"},
            ],
            tools=[_RULE_TOOL],
            tool_choice={"type": "function", "function": {"name": "emit_rule"}},
        )
        data = _first_tool_args(resp)
        if not data or not data.get("applicable"):
            continue
        pred = {
            "op": "cmp",
            "metric": data.get("metric"),
            "comparator": data.get("comparator"),
            "value": data.get("value"),
        }
        ok, _ = validate_predicate(pred)
        if not ok:
            continue
        applies: dict[str, Any] = {}
        if data.get("element"):
            applies["element"] = data["element"]
        if data.get("room_types"):
            applies["room_types"] = data["room_types"]
        confidence = float(data.get("confidence", 0.6))
        if not is_executable(pred):
            confidence = min(confidence, 0.69)  # not evaluable yet -> flag for review
        rule = {
            "id": f"{chunk.section.lower().replace('.', '-')}-{data.get('metric', 'rule')}",
            "category": data.get("category", "other"),
            "applies_to": applies,
            "predicate": pred,
            "severity": data.get("severity", "warning"),
            "citation": chunk.citation(),
        }
        out.rules.append(
            ExtractedRule(rule=rule, confidence=round(confidence, 2),
                          source_chunk_id=chunk.id, source_text=chunk.text)
        )
    return out


def _first_tool_args(resp: Any) -> dict[str, Any] | None:  # pragma: no cover
    choices = getattr(resp, "choices", None)
    if not choices:
        return None
    tool_calls = getattr(choices[0].message, "tool_calls", None)
    if not tool_calls:
        return None
    args = tool_calls[0].function.arguments
    return json.loads(args) if isinstance(args, str) else dict(args)
