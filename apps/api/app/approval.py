"""Approval state machine (pure). Drives the client-approval workflow (Phase 17)."""

from __future__ import annotations

import enum


class ApprovalState(enum.StrEnum):
    draft = "draft"
    shared = "shared"
    in_review = "in_review"
    changes_requested = "changes_requested"
    approved = "approved"
    archived = "archived"


# Allowed forward transitions.
ALLOWED: dict[str, set[str]] = {
    ApprovalState.draft: {ApprovalState.shared, ApprovalState.archived},
    ApprovalState.shared: {
        ApprovalState.in_review,
        ApprovalState.changes_requested,
        ApprovalState.approved,
        ApprovalState.archived,
    },
    ApprovalState.in_review: {
        ApprovalState.changes_requested,
        ApprovalState.approved,
        ApprovalState.archived,
    },
    ApprovalState.changes_requested: {
        ApprovalState.shared,
        ApprovalState.in_review,
        ApprovalState.archived,
    },
    ApprovalState.approved: {ApprovalState.archived},
    ApprovalState.archived: set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in ALLOWED.get(current, set())
