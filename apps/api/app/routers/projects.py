from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import get_db, oid, serialize, utcnow
from ..deps import WRITE_ROLES, authorize_project, get_current_user
from ..errors import ProblemError
from ..models import MEMBERSHIPS, PROJECTS, Role
from ..schemas_api import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    memberships = await db[MEMBERSHIPS].find({"user_id": user["id"]}).to_list(None)
    writable = {m["org_id"]: Role(m["role"]) for m in memberships if Role(m["role"]) in WRITE_ROLES}
    if not writable:
        raise ProblemError(403, "No organization with write access")
    org_id = str(body.org_id) if body.org_id else next(iter(writable))
    if org_id not in writable:
        raise ProblemError(403, "Cannot create projects in this organization")

    now = utcnow()
    doc = {
        "_id": oid(),
        "org_id": org_id,
        "name": body.name,
        "units": body.units,
        "jurisdiction_id": body.jurisdiction_id,
        "boundary_id": None,
        "program_id": None,
        "current_plan_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db[PROJECTS].insert_one(doc)
    return serialize(doc)  # type: ignore[return-value]


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Any]:
    org_ids = [
        m["org_id"] for m in await db[MEMBERSHIPS].find({"user_id": user["id"]}).to_list(None)
    ]
    if not org_ids:
        return []
    docs = await db[PROJECTS].find({"org_id": {"$in": org_ids}}).sort("created_at", -1).to_list(None)
    return [serialize(d) for d in docs]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    project, _role = await authorize_project(db, str(project_id), user)
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user, write=True)
    patch: dict[str, Any] = {
        k: (str(v) if isinstance(v, uuid.UUID) else v)
        for k, v in body.model_dump(exclude_unset=True).items()
    }
    patch["updated_at"] = utcnow()
    await db[PROJECTS].update_one({"_id": str(project_id)}, {"$set": patch})
    return serialize(await db[PROJECTS].find_one({"_id": str(project_id)}))  # type: ignore[return-value]


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    _project, role = await authorize_project(db, str(project_id), user, write=True)
    if role != Role.owner:
        raise ProblemError(403, "Only an owner can delete a project")
    await db[PROJECTS].delete_one({"_id": str(project_id)})
