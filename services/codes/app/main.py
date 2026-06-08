"""Codes service (Phase 07): building-code ingestion + RAG + rule extraction.

Two outputs from one pipeline: a retrieval index for clause Q&A/citations, and a structured,
human-reviewable RuleSet of executable predicates the validator (Phase 09) and generator (Phase 08)
consume. Compliance output is decision-support, not legal sign-off.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .service import DISCLAIMER, CodesService

__version__ = "0.1.0"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "codes")

app = FastAPI(title=f"FPG {SERVICE_NAME}", version=__version__)
service = CodesService()


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    service: str
    version: str


class QueryRequest(BaseModel):
    jurisdiction_id: str
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class IngestRequest(BaseModel):
    jurisdiction_id: str
    text: str | None = None  # inline doc text for re-ingest (e.g. an amended clause)
    version: str | None = None


class UploadRequest(BaseModel):
    jurisdiction_id: str = Field(min_length=1)
    jurisdiction_name: str | None = None
    doc_title: str = Field(min_length=1)
    text: str = Field(min_length=1, description="Plain text / markdown / HTML of the code document.")
    version: str = "1.0"
    publish: bool = True


class ReviewRequest(BaseModel):
    action: str = Field(description="approve | reject | edit")
    rule: dict[str, Any] | None = None


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    return VersionResponse(service=SERVICE_NAME, version=__version__)


@app.get("/codes", tags=["codes"])
async def list_codes(jurisdiction: str | None = None) -> list[dict[str, Any]]:
    return service.list_jurisdictions(jurisdiction)


@app.post("/codes/query", tags=["codes"])
async def query_codes(req: QueryRequest) -> dict[str, Any]:
    if service.get_draft(req.jurisdiction_id) is None:
        raise HTTPException(404, f"unknown jurisdiction: {req.jurisdiction_id}")
    return service.query(req.jurisdiction_id, req.query, req.top_k)


@app.post("/codes/ingest", tags=["codes"])
async def ingest_codes(req: IngestRequest) -> dict[str, Any]:
    try:
        return service.ingest(req.jurisdiction_id, text=req.text, version=req.version)
    except KeyError as exc:
        raise HTTPException(404, f"unknown jurisdiction: {exc}") from exc


@app.post("/codes/upload", tags=["codes"])
async def upload_document(req: UploadRequest) -> dict[str, Any]:
    """Upload a code document for RAG: registers/extends a jurisdiction, ingests + extracts it."""
    result = service.add_document(
        jurisdiction_id=req.jurisdiction_id,
        jurisdiction_name=req.jurisdiction_name or req.jurisdiction_id,
        doc_title=req.doc_title,
        text=req.text,
        version=req.version,
    )
    if req.publish:
        service.publish(req.jurisdiction_id)
    return result


@app.get("/rulesets", tags=["rulesets"])
async def list_rulesets() -> list[dict[str, Any]]:
    out = []
    for jid in service.drafts:
        draft = service.get_draft(jid)
        if draft is not None:
            out.append(draft.summary())
    return out


@app.get("/rulesets/{ruleset_id}", tags=["rulesets"])
async def get_ruleset(ruleset_id: str, include_draft: bool = False) -> dict[str, Any]:
    if include_draft:
        draft = service.get_draft(ruleset_id)
        if draft is None:
            raise HTTPException(404, "RuleSet not found")
        return {**draft.published_doc(), "rules": [r.rule for r in draft.rules]}
    doc = service.get_published(ruleset_id)
    if doc is None:
        raise HTTPException(404, "Published RuleSet not found")
    return {**doc, "disclaimer": DISCLAIMER}


@app.get("/rulesets/{ruleset_id}/rules", tags=["rulesets"])
async def get_ruleset_rules(ruleset_id: str) -> dict[str, Any]:
    try:
        return {"rules": service.rules_view(ruleset_id), "disclaimer": DISCLAIMER}
    except KeyError as exc:
        raise HTTPException(404, "RuleSet not found") from exc


@app.post("/rulesets/{ruleset_id}/rules/{rule_id}/review", tags=["rulesets"])
async def review_rule(ruleset_id: str, rule_id: str, req: ReviewRequest) -> dict[str, Any]:
    try:
        rule = service.review(ruleset_id, rule_id, req.action, req.rule)
    except KeyError as exc:
        raise HTTPException(404, f"not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"rule": rule.rule, "review_status": rule.review_status, "confidence": rule.confidence}


@app.post("/rulesets/{ruleset_id}/publish", tags=["rulesets"])
async def publish_ruleset(ruleset_id: str) -> dict[str, Any]:
    try:
        return service.publish(ruleset_id)
    except KeyError as exc:
        raise HTTPException(404, "RuleSet not found") from exc
