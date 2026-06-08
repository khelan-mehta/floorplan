"""Draft RuleSets, review state, versioning and diffs.

A jurisdiction ingest produces a *draft* RuleSet whose rules carry a confidence + review status.
Publishing emits an immutable, schema-shaped RuleSet (Phase 02) containing only the rules a reviewer
has accepted (high-confidence rules are auto-approved; flagged ones must be approved first). Re-
ingesting a changed document produces a new version and a reviewable **diff** rather than a silent
overwrite.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .extract import CONFIDENCE_FLAG_THRESHOLD, ExtractedRule


@dataclass
class RuleSetDraft:
    id: str
    jurisdiction_id: str
    jurisdiction: str
    version: str
    source_docs: list[dict[str, str]]
    rules: list[ExtractedRule]
    status: str = "draft"  # draft | published
    extraction_method: str = "deterministic"

    def rule_by_id(self, rule_id: str) -> ExtractedRule | None:
        return next((r for r in self.rules if r.rule["id"] == rule_id), None)

    def flagged(self) -> list[ExtractedRule]:
        return [r for r in self.rules if r.confidence <= CONFIDENCE_FLAG_THRESHOLD]

    def auto_approve_confident(self) -> None:
        for r in self.rules:
            if r.confidence > CONFIDENCE_FLAG_THRESHOLD and r.review_status == "pending":
                r.review_status = "approved"

    def published_rules(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(r.rule) for r in self.rules if r.review_status == "approved"]

    def published_doc(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.id,
            "jurisdiction": self.jurisdiction,
            "version": self.version,
            "source_docs": self.source_docs,
            "rules": self.published_rules(),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "jurisdiction_id": self.jurisdiction_id,
            "jurisdiction": self.jurisdiction,
            "version": self.version,
            "status": self.status,
            "extraction_method": self.extraction_method,
            "rule_count": len(self.rules),
            "approved_count": sum(1 for r in self.rules if r.review_status == "approved"),
            "flagged_count": len(self.flagged()),
            "categories": sorted({r.rule["category"] for r in self.rules}),
        }


@dataclass
class RuleDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[dict[str, Any]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def to_dict(self) -> dict[str, Any]:
        return {"added": self.added, "removed": self.removed, "changed": self.changed}


def diff_rulesets(old: RuleSetDraft | None, new: RuleSetDraft) -> RuleDiff:
    """Diff two drafts by rule id + predicate, for a reviewable changelog on re-ingest."""
    diff = RuleDiff()
    if old is None:
        diff.added = [r.rule["id"] for r in new.rules]
        return diff
    old_by_id = {r.rule["id"]: r for r in old.rules}
    new_by_id = {r.rule["id"]: r for r in new.rules}
    diff.added = sorted(set(new_by_id) - set(old_by_id))
    diff.removed = sorted(set(old_by_id) - set(new_by_id))
    for rid in sorted(set(old_by_id) & set(new_by_id)):
        o, n = old_by_id[rid].rule, new_by_id[rid].rule
        if o.get("predicate") != n.get("predicate") or o.get("severity") != n.get("severity"):
            diff.changed.append(
                {"id": rid, "before": o.get("predicate"), "after": n.get("predicate")}
            )
    return diff
