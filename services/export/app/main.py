"""Export service (Phase 15): Plan -> DXF (AIA layers) + IFC4 (spatial tree + spaces)."""

import os
from typing import Any

from fastapi import FastAPI, Response
from pydantic import BaseModel

from .dxf_export import build_dxf_bytes, room_schedule_csv
from .ifc_export import build_ifc_bytes, ifc_stats

__version__ = "0.0.1"
SERVICE_NAME = os.environ.get("SERVICE_NAME", "export")

app = FastAPI(title=f"FPG {SERVICE_NAME}", version=__version__)


class HealthResponse(BaseModel):
    status: str
    service: str


class VersionResponse(BaseModel):
    service: str
    version: str


class ExportRequest(BaseModel):
    plan: dict[str, Any]


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=SERVICE_NAME)


@app.get("/version", response_model=VersionResponse, tags=["meta"])
async def version() -> VersionResponse:
    return VersionResponse(service=SERVICE_NAME, version=__version__)


@app.post("/export/dxf", tags=["export"])
async def export_dxf(req: ExportRequest) -> Response:
    return Response(content=build_dxf_bytes(req.plan), media_type="image/vnd.dxf")


@app.post("/export/ifc", tags=["export"])
async def export_ifc(req: ExportRequest) -> Response:
    return Response(content=build_ifc_bytes(req.plan), media_type="application/x-step")


@app.post("/export/schedule.csv", tags=["export"])
async def export_schedule(req: ExportRequest) -> Response:
    return Response(content=room_schedule_csv(req.plan), media_type="text/csv")


@app.post("/export/stats", tags=["export"])
async def export_stats(req: ExportRequest) -> dict[str, Any]:
    return {"ifc": ifc_stats(req.plan)}
