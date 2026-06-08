import json
from pathlib import Path

import pytest

from app.solidify import scene_stats, solidify_to_glb

EXAMPLES = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "examples"


@pytest.fixture(scope="module")
def plan() -> dict:
    return json.loads((EXAMPLES / "plan-2bed.example.json").read_text(encoding="utf-8"))


def test_stats_match_plan(plan) -> None:
    stats = scene_stats(plan)
    level = plan["levels"][0]
    assert stats["slabs"] == len(level["rooms"])
    assert stats["walls"] == len(level["walls"])
    assert stats["vertices"] > 0


def test_glb_is_produced(plan) -> None:
    glb = solidify_to_glb(plan)
    assert isinstance(glb, bytes)
    assert len(glb) > 100
    assert glb[:4] == b"glTF"  # GLB magic header


def test_empty_plan_does_not_crash() -> None:
    glb = solidify_to_glb({"id": "x", "levels": []})
    assert glb[:4] == b"glTF"
