from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from ..db import get_db
from ..deps import get_current_user
from ..errors import ProblemError
from ..models import RULE_SETS
from ..service_clients import call_service
from ..settings import settings

router = APIRouter(tags=["codes"])


class CodeQuery(BaseModel):
    jurisdiction_id: str
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class CodeUpload(BaseModel):
    jurisdiction_id: str = Field(min_length=1)
    jurisdiction_name: str | None = None
    doc_title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    version: str = "1.0"


@router.get("/codes")
async def list_codes(
    jurisdiction: str | None = None,
    _user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[dict]:
    query = {"jurisdiction": jurisdiction} if jurisdiction else {}
    rule_sets = await db[RULE_SETS].find(query).to_list(None)
    return [
        {"id": rs["_id"], "jurisdiction": rs["jurisdiction"], "version": rs["version"]}
        for rs in rule_sets
    ]


@router.post("/codes/query")
async def query_codes(
    body: CodeQuery,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Proxy the "ask the code" semantic search to the codes RAG service (Phase 07)."""
    try:
        return await call_service(
            settings.codes_url,
            "POST",
            "/codes/query",
            json=body.model_dump(),
        )
    except Exception as exc:  # surface any transport/HTTP failure as a clean 502
        raise ProblemError(502, "Codes service unavailable", str(exc)) from exc


@router.post("/codes/upload")
async def upload_code(
    body: CodeUpload,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Proxy a code-document upload to the codes RAG service (ingest + extract)."""
    try:
        return await call_service(
            settings.codes_url, "POST", "/codes/upload", json=body.model_dump()
        )
    except Exception as exc:
        raise ProblemError(502, "Codes service unavailable", str(exc)) from exc


@router.get("/rulesets/{ruleset_id}")
async def get_ruleset(
    ruleset_id: str,
    _user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict:
    rs = await db[RULE_SETS].find_one({"_id": ruleset_id})
    if rs is None:
        raise ProblemError(404, "RuleSet not found")
    return rs["doc"]
