"""Canonical FPG domain model for Python.

The JSON Schemas in ``packages/schemas/schemas`` are the single source of truth. This package
validates documents against them (``validate``) and provides the deterministic geometry invariant
checks (``geometry``). Pydantic models are generated on demand into ``gen/python/models.py`` via
``pnpm --filter @fpg/schemas codegen:py`` (datamodel-code-generator).
"""

from .geometry import (
    GeometryIssue,
    is_ccw,
    lint_boundary,
    lint_plan,
    lint_polygon,
    ring_self_intersects,
    signed_area,
)
from .room_types import KNOWN_ROOM_TYPES, is_known_room_type
from .validate import (
    SCHEMA_IDS,
    assert_valid,
    is_valid,
    validate,
)

__all__ = [
    "KNOWN_ROOM_TYPES",
    "SCHEMA_IDS",
    "GeometryIssue",
    "assert_valid",
    "is_ccw",
    "is_known_room_type",
    "is_valid",
    "lint_boundary",
    "lint_plan",
    "lint_polygon",
    "ring_self_intersects",
    "signed_area",
    "validate",
]
