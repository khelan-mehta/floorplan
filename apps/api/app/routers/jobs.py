from __future__ import annotations

import asyncio
import uuid
from typing import Any

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import db as global_db
from ..db import get_db, serialize
from ..deps import authorize_project, get_current_user, get_role_in_org
from ..errors import ProblemError
from ..jobs import JOB_GENERATE, enqueue_job, run_generate
from ..models import JOBS, PROJECTS, JobStatus
from ..schemas_api import GenerateRequest, JobOut
from ..security import decode_token

router = APIRouter(tags=["jobs"])

_TERMINAL = {JobStatus.succeeded.value, JobStatus.failed.value}


@router.post("/projects/{project_id}/generate", response_model=JobOut, status_code=202)
async def generate(
    project_id: uuid.UUID,
    body: GenerateRequest,
    background: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    await authorize_project(db, str(project_id), user, write=True)
    params = {"count": body.count, "seed": body.seed or 0, "options": body.options}
    job, cached = await enqueue_job(
        db, type_=JOB_GENERATE, project_id=str(project_id), params=params
    )
    if not cached:
        background.add_task(run_generate, job["id"])
    return job


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    job = await db[JOBS].find_one({"_id": str(job_id)})
    if job is None:
        raise ProblemError(404, "Job not found")
    if job.get("project_id"):
        await authorize_project(db, job["project_id"], user)
    return serialize(job)  # type: ignore[return-value]


@router.websocket("/ws/jobs/{job_id}")
async def job_progress(websocket: WebSocket, job_id: uuid.UUID) -> None:
    """Stream job progress. Auth via `?token=<access token>` query param."""
    from ..progress import broker

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = decode_token(token, expected_type="access")
        user_id = str(payload["sub"])
    except (jwt.PyJWTError, KeyError):
        await websocket.close(code=4401)
        return

    queue = broker.subscribe(str(job_id))
    await websocket.accept()
    try:
        job = await global_db[JOBS].find_one({"_id": str(job_id)})
        if job is None:
            await websocket.close(code=4404)
            return
        if job.get("project_id"):
            project = await global_db[PROJECTS].find_one({"_id": job["project_id"]})
            role = await get_role_in_org(global_db, project["org_id"], user_id) if project else None
            if role is None:
                await websocket.close(code=4403)
                return
        snapshot = {
            "status": job["status"],
            "progress": job["progress"],
            "result": job.get("result"),
        }

        await websocket.send_json(snapshot)
        if snapshot["status"] in _TERMINAL:
            return

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60.0)
            except TimeoutError:
                await websocket.send_json({"status": "heartbeat"})
                continue
            await websocket.send_json(event)
            if event.get("status") in _TERMINAL:
                return
    except WebSocketDisconnect:
        pass
    finally:
        broker.unsubscribe(str(job_id), queue)
