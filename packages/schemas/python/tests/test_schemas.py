"""Python-side schema validation, round-trip, and geometry tests.

Cross-language equality with the TypeScript side is guaranteed by construction: both validate the
SAME JSON Schemas against the SAME fixtures. This file asserts the Python half of that contract.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from fpg_schemas import (
    is_valid,
    lint_boundary,
    lint_plan,
    lint_polygon,
    signed_area,
    validate,
)

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

CASES = [
    ("project.example.json", "project.schema.json"),
    ("boundary-rect.example.json", "boundary.schema.json"),
    ("boundary-lshape.example.json", "boundary.schema.json"),
    ("boundary-two-level.example.json", "boundary.schema.json"),
    ("program-2bed.example.json", "program-graph.schema.json"),
    ("plan-2bed.example.json", "plan.schema.json"),
    ("ruleset.example.json", "ruleset.schema.json"),
    ("ruleset-generic-ibc.example.json", "ruleset.schema.json"),
    ("validation-report.example.json", "validation-report.schema.json"),
]


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(("fixture", "schema_id"), CASES)
def test_fixture_validates(fixture: str, schema_id: str) -> None:
    data = _load(fixture)
    errors = validate(schema_id, data)
    assert errors == [], errors


@pytest.mark.parametrize(("fixture", "schema_id"), CASES)
def test_round_trip(fixture: str, schema_id: str) -> None:
    data = _load(fixture)
    again = json.loads(json.dumps(data))
    assert is_valid(schema_id, again)
    assert again == data


def test_rejects_missing_required() -> None:
    bad = _load("project.example.json")
    del bad["name"]
    assert not is_valid("project.schema.json", bad)


def test_rejects_wrong_schema_version() -> None:
    bad = _load("project.example.json")
    bad["schema_version"] = 2
    assert not is_valid("project.schema.json", bad)


def test_rejects_additional_properties() -> None:
    bad = _load("project.example.json")
    bad["surprise"] = True
    assert not is_valid("project.schema.json", bad)


def test_rectangle_area_is_80_sqm_and_ccw() -> None:
    b = _load("boundary-rect.example.json")
    ring = [(p[0], p[1]) for p in b["levels"][0]["outline"]["rings"][0]["points"]]
    assert signed_area(ring) == 80_000_000
    assert signed_area(ring) > 0


def test_example_geometry_passes_lint() -> None:
    assert lint_boundary(_load("boundary-rect.example.json")) == []
    assert lint_boundary(_load("boundary-lshape.example.json")) == []
    assert lint_boundary(_load("boundary-two-level.example.json")) == []
    assert lint_plan(_load("plan-2bed.example.json")) == []


def test_flags_clockwise_outer_ring() -> None:
    cw = {"rings": [{"points": [[0, 0], [0, 8000], [10000, 8000], [10000, 0]]}]}
    issues = lint_polygon(cw, "/test")
    assert any(i.code == "outer_not_ccw" for i in issues)


def test_flags_self_intersection() -> None:
    bowtie = {"rings": [{"points": [[0, 0], [10000, 10000], [10000, 0], [0, 10000]]}]}
    issues = lint_polygon(bowtie, "/test")
    assert any(i.code == "self_intersection" for i in issues)


def test_cross_language_fixture_parity() -> None:
    # Every fixture used by the TS tests must also exist and validate here.
    assert len(CASES) == 9
    for fixture, schema_id in CASES:
        assert deepcopy(_load(fixture)) is not None
        assert is_valid(schema_id, _load(fixture))
