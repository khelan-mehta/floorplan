from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import get_db, oid, utcnow
from ..deps import authorize_project, get_current_user
from ..domain_validation import assert_document
from ..errors import ProblemError
from ..models import BOUNDARIES, PROJECTS

router = APIRouter(prefix="/projects/{project_id}", tags=["boundary"])


@router.put("/boundary", status_code=200)
async def put_boundary(
    project_id: uuid.UUID,
    doc: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user, write=True)
    assert_document("boundary.schema.json", doc)
    bid = oid()
    await db[BOUNDARIES].insert_one(
        {"_id": bid, "project_id": str(project_id), "doc": doc, "created_at": utcnow()}
    )
    await db[PROJECTS].update_one({"_id": str(project_id)}, {"$set": {"boundary_id": bid}})
    return {"id": bid, "doc": doc}


@router.get("/boundary")
async def get_boundary(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user)
    boundary = await db[BOUNDARIES].find_one(
        {"project_id": str(project_id)}, sort=[("created_at", -1)]
    )
    if boundary is None:
        raise ProblemError(404, "No boundary set for this project")
    return {"id": boundary["_id"], "doc": boundary["doc"]}
