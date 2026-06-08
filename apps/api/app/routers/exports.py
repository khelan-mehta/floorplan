from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import get_db
from ..deps import authorize_project, get_current_user
from ..errors import ProblemError
from ..models import PLANS
from ..settings import settings

router = APIRouter(tags=["export"])

_FORMATS = {
    "dxf": ("/export/dxf", "image/vnd.dxf", "dxf"),
    "ifc": ("/export/ifc", "application/x-step", "ifc"),
    "csv": ("/export/schedule.csv", "text/csv", "csv"),
}


@router.post("/plans/{plan_id}/export")
async def export_plan(
    plan_id: uuid.UUID,
    fmt: str = Query("dxf", alias="format"),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Response:
    spec = _FORMATS.get(fmt)
    if spec is None:
        raise ProblemError(400, "Unsupported export format", f"format={fmt}")
    path, media, ext = spec

    plan = await db[PLANS].find_one({"_id": str(plan_id)})
    if plan is None:
        raise ProblemError(404, "Plan not found")
    await authorize_project(db, plan["project_id"], user)

    try:
        async with httpx.AsyncClient(base_url=settings.export_url, timeout=60.0) as client:
            resp = await client.post(path, json={"plan": plan["doc"]})
            resp.raise_for_status()
            content = resp.content
    except httpx.HTTPError as exc:
        raise ProblemError(502, "Export service unavailable", str(exc)) from exc

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="plan-{plan_id}.{ext}"'},
    )
