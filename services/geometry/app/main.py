"""Geometry service (Phase 11): solidify a Plan into a 3D scene and export GLB."""

import base64
import os
from typing import Any

from fastapi import FastAPI, Response
from pydantic import BaseModel

from .solidify import scene_stats, solidify_to_glb

__version__ = "0.0.1"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "geometry")

app = FastAPI(title=f"FPG {SERVICE_NAME}", version=__version__)


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    service: str
    version: str


class SolidifyRequest(BaseModel):
    plan: dict[str, Any]


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    return VersionResponse(service=SERVICE_NAME, version=__version__)


@app.post("/solidify.glb", tags=["geometry"])
async def solidify_glb(req: SolidifyRequest) -> Response:
    """Return the model as a binary GLB."""
    return Response(content=solidify_to_glb(req.plan), media_type="model/gltf-binary")


@app.post("/solidify", tags=["geometry"])
async def solidify_json(req: SolidifyRequest) -> dict[str, Any]:
    """Return GLB (base64) + scene stats (for storage/embedding)."""
    glb = solidify_to_glb(req.plan)
    return {"stats": scene_stats(req.plan), "glb_base64": base64.b64encode(glb).decode()}
