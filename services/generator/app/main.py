"""Generator service: deterministic layout solver (Phase 08).

Health/version follow the shared stub convention; `/generate` turns a Boundary + ProgramGraph into
ranked candidate Plan documents.
"""

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .solver import generate_layouts

__version__ = "0.0.1"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "generator")

app = FastAPI(title=f"FPG {SERVICE_NAME}", version=__version__)


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    service: str
    version: str


class GenerateRequest(BaseModel):
    boundary: dict[str, Any]
    program: dict[str, Any]
    count: int = Field(default=4, ge=1, le=24)
    seed: int = 0


class GenerateResponse(BaseModel):
    plans: list[dict[str, Any]]


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    return VersionResponse(service=SERVICE_NAME, version=__version__)


@app.post("/generate", response_model=GenerateResponse, tags=["generator"])
async def generate(req: GenerateRequest) -> GenerateResponse:
    plans = generate_layouts(req.boundary, req.program, count=req.count, seed=req.seed)
    return GenerateResponse(plans=plans)
