from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, UploadFile
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import get_db, oid, utcnow
from ..deps import authorize_project, get_current_user
from ..domain_validation import assert_document
from ..errors import ProblemError
from ..models import PROGRAM_GRAPHS, PROJECTS

router = APIRouter(prefix="/projects/{project_id}", tags=["program"])


@router.put("/program", status_code=200)
async def put_program(
    project_id: uuid.UUID,
    doc: dict[str, Any] = Body(...),
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user, write=True)
    assert_document("program-graph.schema.json", doc)
    pid = oid()
    await db[PROGRAM_GRAPHS].insert_one(
        {"_id": pid, "project_id": str(project_id), "doc": doc, "created_at": utcnow()}
    )
    await db[PROJECTS].update_one({"_id": str(project_id)}, {"$set": {"program_id": pid}})
    return {"id": pid, "doc": doc}


@router.get("/program")
async def get_program(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user)
    program = await db[PROGRAM_GRAPHS].find_one(
        {"project_id": str(project_id)}, sort=[("created_at", -1)]
    )
    if program is None:
        raise ProblemError(404, "No program set for this project")
    return {"id": program["_id"], "doc": program["doc"]}


@router.post("/program/import", status_code=501)
async def import_program(
    project_id: uuid.UUID,
    file: UploadFile,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    # Spreadsheet parsing is implemented client-side (Phase 06); a server pipeline is a follow-up.
    await authorize_project(db, str(project_id), user, write=True)
    raise ProblemError(
        501, "Server-side area-program import not implemented", "Use the web Program editor import."
    )
