import json
from pathlib import Path

import pytest

from app.domain_validation import assert_document, validate_document
from app.errors import ProblemError

EXAMPLES = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "examples"


def _load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_valid_boundary_passes() -> None:
    assert validate_document("boundary.schema.json", _load("boundary-rect.example.json")) == []


def test_invalid_boundary_fails() -> None:
    bad = _load("boundary-rect.example.json")
    del bad["levels"]
    assert validate_document("boundary.schema.json", bad)


def test_assert_document_raises_problem() -> None:
    bad = _load("plan-2bed.example.json")
    bad["schema_version"] = 99
    with pytest.raises(ProblemError) as exc:
        assert_document("plan.schema.json", bad)
    assert exc.value.status_code == 422
