from app.routers.plans import _pick_best_candidate


def test_pick_best_candidate_prefers_highest_adjacency() -> None:
    docs = [
        {"id": "a", "score": 80.0, "score_breakdown": {"adjacency": 70.0, "area_fit": 90.0}},
        {"id": "b", "score": 77.0, "score_breakdown": {"adjacency": 85.0, "area_fit": 70.0}},
        {"id": "c", "score": 79.0, "score_breakdown": {"adjacency": 60.0, "area_fit": 95.0}},
    ]
    assert _pick_best_candidate(docs)["id"] == "b"


def test_pick_best_candidate_falls_back_to_score_without_breakdown() -> None:
    docs = [
        {"id": "a", "score": 80.0},
        {"id": "b", "score": 90.0},
    ]
    assert _pick_best_candidate(docs)["id"] == "b"


def test_pick_best_candidate_ties_broken_by_score() -> None:
    docs = [
        {"id": "a", "score": 70.0, "score_breakdown": {"adjacency": 90.0, "area_fit": 50.0}},
        {"id": "b", "score": 95.0, "score_breakdown": {"adjacency": 90.0, "area_fit": 100.0}},
    ]
    assert _pick_best_candidate(docs)["id"] == "b"
