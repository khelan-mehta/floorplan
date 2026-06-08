from __future__ import annotations

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..approval import ApprovalState, can_transition
from ..db import get_db, oid, serialize, utcnow
from ..deps import authorize_project, get_current_user
from ..errors import ProblemError
from ..models import APPROVALS, AUDIT_LOG, COMMENTS, PLANS, PROJECTS, SHARES
from ..schemas_api import (
    ApprovalOut,
    ApprovalUpdate,
    AuditOut,
    CommentCreate,
    CommentOut,
    ShareCreate,
    ShareOut,
)
from ..settings import settings

router = APIRouter(tags=["collab"])


async def _audit(
    db: AsyncIOMotorDatabase, project_id: str, action: str, actor: str, **meta: Any
) -> None:
    await db[AUDIT_LOG].insert_one(
        {
            "_id": oid(),
            "project_id": project_id,
            "action": action,
            "actor": actor,
            "meta": meta,
            "created_at": utcnow(),
        }
    )


def _share_url(token: str) -> str:
    base = settings.cors_origins[0] if settings.cors_origins else "http://localhost:5173"
    return f"{base}/shared/{token}"


# --- sharing ---
@router.post("/projects/{project_id}/shares", response_model=ShareOut, status_code=201)
async def create_share(
    project_id: uuid.UUID,
    body: ShareCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user, write=True)
    token = secrets.token_urlsafe(24)
    doc = {
        "_id": oid(),
        "project_id": str(project_id),
        "token": token,
        "role": body.role,
        "created_by": user["id"],
        "created_at": utcnow(),
    }
    await db[SHARES].insert_one(doc)
    await _audit(db, str(project_id), "share.create", user["name"], role=body.role)
    return {**(serialize(doc) or {}), "url": _share_url(token)}


@router.get("/projects/{project_id}/shares", response_model=list[ShareOut])
async def list_shares(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Any]:
    await authorize_project(db, str(project_id), user)
    shares = await db[SHARES].find({"project_id": str(project_id)}).to_list(None)
    return [{**(serialize(s) or {}), "url": _share_url(s["token"])} for s in shares]


async def _resolve_share(db: AsyncIOMotorDatabase, token: str) -> dict[str, Any]:
    share = await db[SHARES].find_one({"token": token})
    if share is None:
        raise ProblemError(404, "Invalid share link")
    return share


# --- capability-URL client access (no account) ---
@router.get("/shared/{token}")
async def shared_view(token: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> dict[str, Any]:
    share = await _resolve_share(db, token)
    project = await db[PROJECTS].find_one({"_id": share["project_id"]})
    if project is None:
        raise ProblemError(404, "Project not found")
    plans = await db[PLANS].find({"project_id": project["_id"]}).sort("created_at", -1).to_list(None)
    comments = await db[COMMENTS].find({"project_id": project["_id"]}).to_list(None)
    return {
        "project": {"id": project["_id"], "name": project["name"]},
        "role": share["role"],
        "plans": [{"id": p["_id"], "score": p.get("score"), "doc": p["doc"]} for p in plans],
        "comments": [serialize(c) for c in comments],
    }


@router.post("/shared/{token}/comments", response_model=CommentOut, status_code=201)
async def shared_comment(
    token: str, body: CommentCreate, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict[str, Any]:
    share = await _resolve_share(db, token)
    doc = {
        "_id": oid(),
        "project_id": share["project_id"],
        "plan_id": str(body.plan_id) if body.plan_id else None,
        "author": body.author_name or f"client ({share['role']})",
        "body": body.body,
        "anchor": body.anchor,
        "resolved": False,
        "created_at": utcnow(),
    }
    await db[COMMENTS].insert_one(doc)
    await _audit(db, share["project_id"], "comment.create", doc["author"], via="share")
    return serialize(doc)  # type: ignore[return-value]


# --- authenticated comments ---
@router.post("/projects/{project_id}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    project_id: uuid.UUID,
    body: CommentCreate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user, comment=True)
    doc = {
        "_id": oid(),
        "project_id": str(project_id),
        "plan_id": str(body.plan_id) if body.plan_id else None,
        "author": user["name"],
        "body": body.body,
        "anchor": body.anchor,
        "resolved": False,
        "created_at": utcnow(),
    }
    await db[COMMENTS].insert_one(doc)
    return serialize(doc)  # type: ignore[return-value]


@router.get("/projects/{project_id}/comments", response_model=list[CommentOut])
async def list_comments(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Any]:
    await authorize_project(db, str(project_id), user)
    docs = (
        await db[COMMENTS].find({"project_id": str(project_id)}).sort("created_at", 1).to_list(None)
    )
    return [serialize(d) for d in docs]


@router.post("/comments/{comment_id}/resolve", response_model=CommentOut)
async def resolve_comment(
    comment_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    comment = await db[COMMENTS].find_one({"_id": str(comment_id)})
    if comment is None:
        raise ProblemError(404, "Comment not found")
    await authorize_project(db, comment["project_id"], user, write=True)
    await db[COMMENTS].update_one({"_id": str(comment_id)}, {"$set": {"resolved": True}})
    comment["resolved"] = True
    return serialize(comment)  # type: ignore[return-value]


# --- approval workflow ---
async def _latest_approval(db: AsyncIOMotorDatabase, plan_id: str) -> dict[str, Any] | None:
    return await db[APPROVALS].find_one({"plan_id": plan_id}, sort=[("created_at", -1)])


@router.post("/plans/{plan_id}/approval", response_model=ApprovalOut, status_code=201)
async def set_approval(
    plan_id: uuid.UUID,
    body: ApprovalUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    plan = await db[PLANS].find_one({"_id": str(plan_id)})
    if plan is None:
        raise ProblemError(404, "Plan not found")
    project, _role = await authorize_project(db, plan["project_id"], user, write=True)

    if body.state not in set(ApprovalState):
        raise ProblemError(400, "Unknown approval state", body.state)
    current = await _latest_approval(db, str(plan_id))
    current_state = current["state"] if current else ApprovalState.draft.value
    if current_state != body.state and not can_transition(current_state, body.state):
        raise ProblemError(409, "Illegal transition", f"{current_state} -> {body.state}")

    if body.state == ApprovalState.approved.value:
        plan_ids = await db[APPROVALS].distinct("plan_id", {"project_id": project["id"]})
        for pid in plan_ids:
            if pid == str(plan_id):
                continue
            latest = await _latest_approval(db, pid)
            if latest and latest["state"] == ApprovalState.approved.value:
                await db[APPROVALS].insert_one(
                    {
                        "_id": oid(),
                        "project_id": project["id"],
                        "plan_id": pid,
                        "state": ApprovalState.archived.value,
                        "note": "superseded",
                        "decided_by": user["id"],
                        "created_at": utcnow(),
                    }
                )
        await db[PROJECTS].update_one(
            {"_id": project["id"]}, {"$set": {"current_plan_id": str(plan_id)}}
        )

    doc = {
        "_id": oid(),
        "project_id": project["id"],
        "plan_id": str(plan_id),
        "state": body.state,
        "note": body.note,
        "decided_by": user["id"],
        "created_at": utcnow(),
    }
    await db[APPROVALS].insert_one(doc)
    await _audit(db, project["id"], f"approval.{body.state}", user["name"], plan_id=str(plan_id))
    return serialize(doc)  # type: ignore[return-value]


@router.get("/projects/{project_id}/audit", response_model=list[AuditOut])
async def list_audit(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Any]:
    await authorize_project(db, str(project_id), user)
    docs = (
        await db[AUDIT_LOG].find({"project_id": str(project_id)}).sort("created_at", -1).to_list(None)
    )
    return [serialize(d) for d in docs]
