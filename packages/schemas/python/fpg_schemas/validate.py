"""Validate documents against the canonical JSON Schemas (Draft 2020-12).

Mirrors the TypeScript ``@fpg/schemas`` validators so both languages accept/reject identically.
"""

from __future__ import annotations

import json
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"

SCHEMA_IDS: tuple[str, ...] = (
    "common.schema.json",
    "project.schema.json",
    "boundary.schema.json",
    "program-graph.schema.json",
    "plan.schema.json",
    "ruleset.schema.json",
    "validation-report.schema.json",
)


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for path in SCHEMAS_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@cache
def _validator(schema_id: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / schema_id).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def validate(schema_id: str, data: Any) -> list[str]:
    """Return a list of human-readable error messages ([] if valid)."""
    validator = _validator(schema_id)
    return [
        f"{'/'.join(str(p) for p in err.absolute_path) or '/'}: {err.message}"
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]


def is_valid(schema_id: str, data: Any) -> bool:
    return not validate(schema_id, data)


def assert_valid(schema_id: str, data: Any) -> None:
    errors = validate(schema_id, data)
    if errors:
        raise ValueError(f"Validation failed for {schema_id}: {'; '.join(errors)}")
