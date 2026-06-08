"""Phase 07 codes service: ingestion, hybrid retrieval, rule extraction, review/publish, diff."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.dsl import validate_predicate
from app.main import app
from app.service import CodesService

JID = "generic-ibc-2021"
EXAMPLES = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "examples"


@pytest.fixture
def svc() -> CodesService:
    return CodesService()


def _key(rule: dict) -> tuple:
    return (
        rule["id"],
        rule["category"],
        rule["severity"],
        json.dumps(rule["predicate"], sort_keys=True),
        json.dumps(rule.get("applies_to", {}), sort_keys=True),
        rule["citation"]["section"],
    )


def test_query_bedroom_area_returns_correct_clause(svc: CodesService) -> None:
    res = svc.query(JID, "minimum bedroom area?", top_k=3)
    assert res["results"], "expected retrieval hits"
    assert res["results"][0]["section"] == "1208.1"
    assert res.get("disclaimer")


def test_seed_publishes_ten_plus_executable_categories(svc: CodesService) -> None:
    pub = svc.get_published(JID)
    assert pub is not None
    cats = {r["category"] for r in pub["rules"]}
    assert len(cats) >= 10, cats
    for r in pub["rules"]:
        ok, reason = validate_predicate(r["predicate"])
        assert ok, f"{r['id']}: {reason}"
        assert r["citation"]["section"] and r["citation"]["text"]


def test_extraction_matches_canonical_example(svc: CodesService) -> None:
    example = json.loads((EXAMPLES / "ruleset-generic-ibc.example.json").read_text())
    draft = svc.get_draft(JID)
    assert draft is not None
    got = sorted(_key(r.rule) for r in draft.rules)
    want = sorted(_key(r) for r in example["rules"])
    assert got == want


def test_low_confidence_rule_is_flagged_and_excluded(svc: CodesService) -> None:
    draft = svc.get_draft(JID)
    assert draft is not None
    flagged_ids = {r.rule["id"] for r in draft.flagged()}
    assert "building-coverage" in flagged_ids
    pub_ids = {r["id"] for r in svc.get_published(JID)["rules"]}
    assert "building-coverage" not in pub_ids


def test_review_then_publish_includes_flagged(svc: CodesService) -> None:
    svc.review(JID, "building-coverage", "approve", None)
    pub = svc.publish(JID)
    assert "building-coverage" in {r["id"] for r in pub["rules"]}


def test_reingest_amended_doc_produces_diff(svc: CodesService) -> None:
    doc = svc.get_draft(JID)
    assert doc is not None
    src = (Path(__file__).resolve().parents[1] / "app/seed_data/generic-ibc.code.md").read_text(
        encoding="utf-8"
    )
    amended = src.replace("280 mm (11 inches)", "300 mm (11 inches)")
    res = svc.ingest(JID, text=amended)
    changed_ids = {c["id"] for c in res["diff"]["changed"]}
    assert "stair-tread-run" in changed_ids
    assert res["ruleset"]["version"] != "2021.0"  # versioned, not silently overwritten


def test_value_parsed_from_prose(svc: CodesService) -> None:
    draft = svc.get_draft(JID)
    assert draft is not None
    bedroom = draft.rule_by_id("min-area-bedroom")
    assert bedroom is not None
    assert bedroom.rule["predicate"]["value"] == 7_000_000  # "7 m²" -> mm^2


# --- HTTP surface -----------------------------------------------------------

client = TestClient(app)


def test_endpoints_smoke() -> None:
    assert client.get("/health").json()["status"] == "ok"

    codes = client.get("/codes").json()
    assert any(c["id"] == JID and c["published"] for c in codes)

    q = client.post("/codes/query", json={"jurisdiction_id": JID, "query": "door width"})
    assert q.status_code == 200
    assert q.json()["results"]

    rs = client.get(f"/rulesets/{JID}").json()
    assert rs["id"] == JID and "disclaimer" in rs

    rules = client.get(f"/rulesets/{JID}/rules").json()["rules"]
    assert len(rules) == 13
    assert any(r["flagged"] for r in rules)

    review = client.post(
        f"/rulesets/{JID}/rules/building-coverage/review", json={"action": "approve"}
    )
    assert review.status_code == 200 and review.json()["review_status"] == "approved"

    pub = client.post(f"/rulesets/{JID}/publish").json()
    assert "building-coverage" in {r["id"] for r in pub["rules"]}


def test_unknown_jurisdiction_404() -> None:
    assert client.post("/codes/query", json={"jurisdiction_id": "nope", "query": "x"}).status_code == 404
