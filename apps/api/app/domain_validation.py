"""Validate domain documents (Boundary, ProgramGraph, Plan, …) against the canonical JSON Schemas.

Loaded from `settings.resolved_schemas_dir()` (Phase 02 is the source of truth). Mirrors
`fpg_schemas.validate` so the API rejects on write exactly as the libraries do.
"""

from __future__ import annotations

import json
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import ProblemError
from .settings import settings


@lru_cache(maxsize=1)
def _registry() -> Registry:
    schemas_dir = Path(settings.resolved_schemas_dir())
    resources = []
    for path in schemas_dir.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@cache
def _validator(schema_id: str) -> Draft202012Validator:
    schemas_dir = Path(settings.resolved_schemas_dir())
    schema = json.loads((schemas_dir / schema_id).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def validate_document(schema_id: str, data: Any) -> list[str]:
    validator = _validator(schema_id)
    return [
        f"{'/'.join(str(p) for p in err.absolute_path) or '/'}: {err.message}"
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    ]


def assert_document(schema_id: str, data: Any) -> None:
    """Raise a 422 ProblemError if `data` does not conform to `schema_id`."""
    errors = validate_document(schema_id, data)
    if errors:
        raise ProblemError(
            status_code=422,
            title="Invalid domain document",
            detail=f"{schema_id} failed validation",
            errors=errors,
        )
