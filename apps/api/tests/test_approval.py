from app.approval import ApprovalState, can_transition


def test_legal_transitions() -> None:
    assert can_transition(ApprovalState.draft, ApprovalState.shared)
    assert can_transition(ApprovalState.shared, ApprovalState.approved)
    assert can_transition(ApprovalState.in_review, ApprovalState.changes_requested)
    assert can_transition(ApprovalState.changes_requested, ApprovalState.shared)
    assert can_transition(ApprovalState.approved, ApprovalState.archived)


def test_illegal_transitions() -> None:
    assert not can_transition(ApprovalState.draft, ApprovalState.approved)
    assert not can_transition(ApprovalState.approved, ApprovalState.shared)
    assert not can_transition(ApprovalState.archived, ApprovalState.draft)
    assert not can_transition(ApprovalState.draft, ApprovalState.in_review)
