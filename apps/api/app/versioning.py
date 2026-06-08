"""Pure helpers for plan versioning, diffing, and idempotency keys. No I/O — easy to unit-test."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def inputs_hash(*parts: Any) -> str:
    """Stable hash of arbitrary JSON-serializable inputs (for idempotent jobs)."""
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def next_plan_doc(
    parent_doc: dict[str, Any],
    *,
    new_id: str,
    patch: dict[str, Any],
    source: str = "edited",
) -> dict[str, Any]:
    """Produce a new immutable plan document from a parent + a shallow patch.

    The result is a fresh document (parent is never mutated) with lineage recorded.
    """
    doc = json.loads(json.dumps(parent_doc))  # deep copy
    doc.update(patch)
    doc["id"] = new_id
    doc["parent_plan_id"] = parent_doc.get("id")
    doc["source"] = source
    return doc


def _walk(prefix: str, value: Any, out: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(f"{prefix}/{k}", v, out)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk(f"{prefix}/{i}", v, out)
    else:
        out[prefix] = value


def diff_docs(a: dict[str, Any], b: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Flat path-based diff between two JSON documents.

    Returns {"added": {...}, "removed": {...}, "changed": {path: {"from":x,"to":y}}}.
    Ignores volatile top-level fields (id, parent_plan_id, created_at).
    """
    ignore = {"/id", "/parent_plan_id", "/created_at"}
    fa: dict[str, Any] = {}
    fb: dict[str, Any] = {}
    _walk("", a, fa)
    _walk("", b, fb)
    added = {k: v for k, v in fb.items() if k not in fa and k not in ignore}
    removed = {k: v for k, v in fa.items() if k not in fb and k not in ignore}
    changed = {
        k: {"from": fa[k], "to": fb[k]}
        for k in fa.keys() & fb.keys()
        if fa[k] != fb[k] and k not in ignore
    }
    return {"added": added, "removed": removed, "changed": changed}
