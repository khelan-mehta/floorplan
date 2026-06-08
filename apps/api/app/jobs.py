"""Job enqueue + execution (MongoDB).

Idempotent by inputs-hash. The `generate` job calls the generator service (Phase 08 solver) to turn
the project's boundary + program into candidate plans, falling back to a trivial single-room STUB if
the service is unreachable. Execution defaults to in-process (FastAPI BackgroundTasks); the Arq
worker runs the SAME executor at scale.
"""

from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from .db import db as global_db
from .db import oid, serialize, utcnow
from .domain_validation import assert_document
from .models import BOUNDARIES, JOBS, PLANS, PROGRAM_GRAPHS, PROJECTS, RULE_SETS, JobStatus
from .progress import broker
from .service_clients import call_service
from .settings import settings
from .versioning import inputs_hash

logger = logging.getLogger("fpg.jobs")

JOB_GENERATE = "generate"
# Bump when the generator algorithm changes so cached results are invalidated and re-run.
ALGO_VERSION = 3


async def _load_ruleset(db: AsyncIOMotorDatabase, project_id: str) -> dict[str, Any] | None:
    """Resolve the published RuleSet for a project's selected jurisdiction (if any)."""
    project = await db[PROJECTS].find_one({"_id": project_id})
    jurisdiction_id = project.get("jurisdiction_id") if project else None
    if not jurisdiction_id:
        return None
    rs = await db[RULE_SETS].find_one({"_id": jurisdiction_id})
    return rs["doc"] if rs else None


async def _validate_plan(
    plan_doc: dict[str, Any], ruleset_doc: dict[str, Any]
) -> dict[str, Any] | None:
    """Score a plan against the ruleset via the validator service. None if unavailable."""
    try:
        return await call_service(
            settings.validator_url,
            "POST",
            "/validate",
            json={"plan": plan_doc, "ruleset": ruleset_doc},
        )
    except Exception as exc:  # validator is optional; fall back to the layout score
        logger.warning("validator unavailable, skipping compliance score: %s", exc)
        return None


async def _content_signature(db: AsyncIOMotorDatabase, type_: str, project_id: str) -> Any:
    """Inputs (beyond count/seed) that must invalidate a cached generate job when they change."""
    if type_ != JOB_GENERATE:
        return None
    boundary = await db[BOUNDARIES].find_one({"project_id": project_id}, sort=[("created_at", -1)])
    program = await db[PROGRAM_GRAPHS].find_one({"project_id": project_id}, sort=[("created_at", -1)])
    project = await db[PROJECTS].find_one({"_id": project_id})
    return {
        "boundary": boundary["doc"] if boundary else None,
        "program": program["doc"] if program else None,
        # jurisdiction drives the compliance score, so it's part of the result identity too
        "jurisdiction_id": project.get("jurisdiction_id") if project else None,
        "algo": ALGO_VERSION,
    }


async def enqueue_job(
    db: AsyncIOMotorDatabase, *, type_: str, project_id: str, params: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Create a job, or return a cached succeeded job with identical inputs (idempotency).

    The key folds in the current boundary/program/jurisdiction so editing the program (e.g. door
    count or rooms) and regenerating produces fresh plans rather than a stale cached result.
    """
    content = await _content_signature(db, type_, project_id)
    ihash = inputs_hash(type_, project_id, params, content)
    cached = await db[JOBS].find_one({"inputs_hash": ihash, "status": JobStatus.succeeded.value})
    if cached is not None:
        return serialize(cached), True  # type: ignore[return-value]
    now = utcnow()
    job = {
        "_id": oid(),
        "project_id": project_id,
        "type": type_,
        "status": JobStatus.queued.value,
        "inputs_hash": ihash,
        "progress": 0.0,
        "params": params,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    await db[JOBS].insert_one(job)
    return serialize(job), False  # type: ignore[return-value]


def _shoelace_area(points: list[list[int]]) -> int:
    total = 0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) // 2


def _centroid(points: list[list[int]]) -> list[int]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [round(sum(xs) / len(xs)), round(sum(ys) / len(ys))]


def _stub_plan_doc(project_id: str, boundary_doc: dict[str, Any] | None, seed: int) -> dict:
    plan_id = oid()
    if boundary_doc and boundary_doc.get("levels"):
        levels_src = boundary_doc["levels"]
    else:
        levels_src = [
            {
                "index": 0,
                "outline": {"rings": [{"points": [[0, 0], [10000, 0], [10000, 8000], [0, 8000]]}]},
            }
        ]
    levels = []
    for lvl in levels_src:
        outer = lvl["outline"]["rings"][0]["points"]
        levels.append(
            {
                "index": lvl["index"],
                "rooms": [
                    {
                        "id": f"room-l{lvl['index']}",
                        "type": "living",
                        "polygon": {"rings": [{"points": outer}]},
                        "area_mm2": _shoelace_area(outer),
                        "centroid": _centroid(outer),
                    }
                ],
                "walls": [],
                "openings": [],
                "fixtures": [],
            }
        )
    return {
        "schema_version": 1,
        "id": plan_id,
        "project_id": project_id,
        "parent_plan_id": None,
        "seed": seed,
        "source": "generated",
        "levels": levels,
    }


async def _candidate_plans(
    boundary_doc: dict[str, Any] | None,
    program_doc: dict[str, Any] | None,
    count: int,
    seed: int,
    project_id: str,
) -> list[dict[str, Any]]:
    if boundary_doc and program_doc:
        try:
            resp = await call_service(
                settings.generator_url,
                "POST",
                "/generate",
                json={
                    "boundary": boundary_doc,
                    "program": program_doc,
                    "count": count,
                    "seed": seed,
                },
            )
            plans = resp.get("plans") if isinstance(resp, dict) else None
            if plans:
                return list(plans)
        except Exception as exc:
            logger.warning("generator service unavailable, using stub: %s", exc)
    return [_stub_plan_doc(project_id, boundary_doc, seed + i) for i in range(count)]


async def run_generate(job_id: str) -> None:
    """Executor for a `generate` job. Safe to call inline (BackgroundTasks) or from Arq."""
    db = global_db
    job = await db[JOBS].find_one({"_id": job_id})
    if job is None:
        return
    project_id = job["project_id"]
    await db[JOBS].update_one({"_id": job_id}, {"$set": {"status": JobStatus.running.value}})
    await broker.publish(job_id, {"status": "running", "progress": 0.0})

    try:
        count = int(job["params"].get("count", 4))
        base_seed = int(job["params"].get("seed", 0))
        boundary = await db[BOUNDARIES].find_one(
            {"project_id": project_id}, sort=[("created_at", -1)]
        )
        program = await db[PROGRAM_GRAPHS].find_one(
            {"project_id": project_id}, sort=[("created_at", -1)]
        )
        boundary_doc = boundary["doc"] if boundary else None
        program_doc = program["doc"] if program else None

        docs = await _candidate_plans(boundary_doc, program_doc, count, base_seed, project_id)
        ruleset_doc = await _load_ruleset(db, project_id)

        plan_ids: list[str] = []
        for i, doc in enumerate(docs):
            doc["project_id"] = project_id
            doc["parent_plan_id"] = None
            assert_document("plan.schema.json", doc)

            # The generator proposes a layout score; the validator disposes a compliance score.
            layout_score = doc.get("score")
            validation = await _validate_plan(doc, ruleset_doc) if ruleset_doc else None
            score = validation["score"] if validation else layout_score

            # Plan ids are deterministic by (project_id, seed) for reproducibility, so an identical
            # re-generation replaces rather than collides (insert would raise a duplicate-key error).
            await db[PLANS].replace_one(
                {"_id": doc["id"]},
                {
                    "_id": doc["id"],
                    "project_id": project_id,
                    "parent_plan_id": None,
                    "source": "generated",
                    "seed": doc.get("seed", base_seed + i),
                    "score": score,
                    "layout_score": layout_score,
                    "validation": validation,
                    "doc": doc,
                    "created_at": utcnow(),
                },
                upsert=True,
            )
            plan_ids.append(doc["id"])
            progress = (i + 1) / len(docs)
            await db[JOBS].update_one({"_id": job_id}, {"$set": {"progress": progress}})
            await broker.publish(
                job_id,
                {"status": "running", "progress": progress, "plan_id": doc["id"], "score": score},
            )

        result = {"plan_ids": plan_ids}
        await db[JOBS].update_one(
            {"_id": job_id},
            {"$set": {"status": JobStatus.succeeded.value, "progress": 1.0, "result": result}},
        )
        await broker.publish(job_id, {"status": "succeeded", "progress": 1.0, "result": result})
    except Exception as exc:
        await db[JOBS].update_one(
            {"_id": job_id}, {"$set": {"status": JobStatus.failed.value, "error": str(exc)}}
        )
        await broker.publish(job_id, {"status": "failed", "error": str(exc)})
