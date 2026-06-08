"""Validator service (Phase 09): score a Plan against a RuleSet -> ValidationReport.

Pure + deterministic. Health/version follow the shared stub convention.
"""

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from .validator import validate

__version__ = "0.0.1"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "validator")

app = FastAPI(title=f"FPG {SERVICE_NAME}", version=__version__)


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    service: str
    version: str


class ValidateRequest(BaseModel):
    plan: dict[str, Any]
    ruleset: dict[str, Any]


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    return VersionResponse(service=SERVICE_NAME, version=__version__)


@app.post("/validate", tags=["validator"])
async def validate_plan(req: ValidateRequest) -> dict[str, Any]:
    return validate(req.plan, req.ruleset)
