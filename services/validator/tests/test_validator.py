import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.validator import validate

REPO = Path(__file__).resolve().parents[3]
SCHEMAS = REPO / "packages" / "schemas" / "schemas"
EXAMPLES = REPO / "packages" / "schemas" / "examples"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ruleset() -> dict:
    return _load(EXAMPLES / "ruleset.example.json")


@pytest.fixture(scope="module")
def plan() -> dict:
    return _load(EXAMPLES / "plan-2bed.example.json")


@pytest.fixture(scope="module")
def report_validator() -> Draft202012Validator:
    resources = [
        (json.loads(p.read_text())["$id"], Resource.from_contents(json.loads(p.read_text())))
        for p in SCHEMAS.glob("*.schema.json")
    ]
    schema = _load(SCHEMAS / "validation-report.schema.json")
    return Draft202012Validator(schema, registry=Registry().with_resources(resources))


def test_clean_plan_passes(plan, ruleset, report_validator) -> None:
    report = validate(plan, ruleset)
    assert report_validator.is_valid(report), list(report_validator.iter_errors(report))
    assert report["score"] == 100.0
    assert all(r["status"] in ("pass", "na") for r in report["results"])


def test_undersized_bedroom_flagged(plan, ruleset) -> None:
    bad = copy.deepcopy(plan)
    room = bad["levels"][0]["rooms"][1]  # the master_bedroom
    room["area_mm2"] = 6_200_000  # below 7 m²
    report = validate(bad, ruleset)
    area_rule = next(r for r in report["results"] if r["rule_id"] == "min-area-bedroom")
    assert area_rule["status"] == "fail"
    assert area_rule["geometry_ref"] == room["id"]
    assert "1208.1" in area_rule["message"]  # citation present
    assert report["score"] < 100


def test_narrow_door_flagged(plan, ruleset) -> None:
    bad = copy.deepcopy(plan)
    bad["levels"][0]["openings"][0]["width_mm"] = 700  # below 815
    report = validate(bad, ruleset)
    door_rule = next(r for r in report["results"] if r["rule_id"] == "min-door-clear-width")
    assert door_rule["status"] == "fail"
    assert door_rule["geometry_ref"] == "d-mid"


def test_deterministic(plan, ruleset) -> None:
    assert validate(plan, ruleset) == validate(plan, ruleset)


def test_category_scores_present(plan, ruleset) -> None:
    report = validate(plan, ruleset)
    assert "min_area" in report["category_scores"]
    assert "door_width" in report["category_scores"]
