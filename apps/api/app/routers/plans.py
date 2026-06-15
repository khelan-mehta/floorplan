from __future__ import annotations

import random
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from .. import critic
from ..db import get_db, oid, serialize, utcnow
from ..deps import authorize_project, get_current_user
from ..domain_validation import assert_document
from ..errors import ProblemError
from ..jobs import _candidate_plans, _load_ruleset, _validate_plan
from ..models import BOUNDARIES, PLANS, PROGRAM_GRAPHS, PROJECTS
from ..schemas_api import CritiqueOut, CritiqueRequest, DiffOut, PlanOut, PlanPatch
from ..versioning import diff_docs, next_plan_doc

router = APIRouter(tags=["plans"])


async def _load(db: AsyncIOMotorDatabase, plan_id: str) -> dict[str, Any]:
    plan = await db[PLANS].find_one({"_id": plan_id})
    if plan is None:
        raise ProblemError(404, "Plan not found")
    return plan


def _pick_best_candidate(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick the candidate plan doc that best satisfies the program's adjacency constraints:
    highest `score_breakdown.adjacency`, falling back to `score`, tie-broken by `score`."""

    def key(doc: dict[str, Any]) -> tuple[float, float]:
        breakdown = doc.get("score_breakdown") or {}
        adjacency = breakdown.get("adjacency")
        overall = doc.get("score") or 0.0
        return (adjacency if adjacency is not None else overall, overall)

    return max(docs, key=key)


@router.get("/projects/{project_id}/plans", response_model=list[PlanOut])
async def list_plans(
    project_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Any]:
    await authorize_project(db, str(project_id), user)
    docs = await db[PLANS].find({"project_id": str(project_id)}).sort("created_at", -1).to_list(None)
    return [serialize(d) for d in docs]


@router.get("/plans/{plan_id}", response_model=PlanOut)
async def get_plan(
    plan_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    plan = await _load(db, str(plan_id))
    await authorize_project(db, plan["project_id"], user)
    return serialize(plan)  # type: ignore[return-value]


@router.patch("/plans/{plan_id}", response_model=PlanOut)
async def patch_plan(
    plan_id: uuid.UUID,
    body: PlanPatch,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    parent = await _load(db, str(plan_id))
    await authorize_project(db, parent["project_id"], user, write=True)

    new_id = oid()
    new_doc = next_plan_doc(parent["doc"], new_id=new_id, patch=body.patch, source=body.source)
    assert_document("plan.schema.json", new_doc)

    # Re-check the edited plan against the project's code (so wall/door/window edits are scored).
    ruleset_doc = await _load_ruleset(db, parent["project_id"])
    validation = await _validate_plan(new_doc, ruleset_doc) if ruleset_doc else None
    score = validation["score"] if validation else new_doc.get("score")

    row = {
        "_id": new_id,
        "project_id": parent["project_id"],
        "parent_plan_id": parent["_id"],
        "source": body.source,
        "seed": parent.get("seed"),
        "score": score,
        "layout_score": parent.get("layout_score"),
        "validation": validation,
        "doc": new_doc,
        "created_at": utcnow(),
    }
    await db[PLANS].insert_one(row)
    await db[PROJECTS].update_one(
        {"_id": parent["project_id"]}, {"$set": {"current_plan_id": new_id}}
    )
    return serialize(row)  # type: ignore[return-value]


@router.post("/plans/{plan_id}/duplicate", response_model=PlanOut, status_code=201)
async def duplicate_plan(
    plan_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    parent = await _load(db, str(plan_id))
    await authorize_project(db, parent["project_id"], user, write=True)
    new_id = oid()
    new_doc = next_plan_doc(parent["doc"], new_id=new_id, patch={}, source="edited")
    assert_document("plan.schema.json", new_doc)
    row = {
        "_id": new_id,
        "project_id": parent["project_id"],
        "parent_plan_id": parent["_id"],
        "source": "edited",
        "seed": parent.get("seed"),
        "score": new_doc.get("score"),
        "doc": new_doc,
        "created_at": utcnow(),
    }
    await db[PLANS].insert_one(row)
    return serialize(row)  # type: ignore[return-value]


@router.get("/plans/{plan_id}/versions", response_model=list[PlanOut])
async def plan_versions(
    plan_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[Any]:
    plan = await _load(db, str(plan_id))
    await authorize_project(db, plan["project_id"], user)
    chain: list[Any] = []
    seen: set[str] = set()
    current: dict[str, Any] | None = plan
    while current is not None and current["_id"] not in seen:
        chain.append(serialize(current))
        seen.add(current["_id"])
        parent_id = current.get("parent_plan_id")
        current = await db[PLANS].find_one({"_id": parent_id}) if parent_id else None
    return chain


@router.post("/plans/{plan_id}/critique", response_model=CritiqueOut, status_code=201)
async def critique_plan(
    plan_id: uuid.UUID,
    body: CritiqueRequest,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    """Apply free-text feedback to a plan: turn it into ProgramGraph adjustments via the AI
    critic, regenerate one candidate from the adjusted program, and store it as a new plan
    version."""
    parent = await _load(db, str(plan_id))
    project_id = parent["project_id"]
    await authorize_project(db, project_id, user, write=True)

    boundary = await db[BOUNDARIES].find_one({"project_id": project_id}, sort=[("created_at", -1)])
    program = await db[PROGRAM_GRAPHS].find_one(
        {"project_id": project_id}, sort=[("created_at", -1)]
    )
    boundary_doc = boundary["doc"] if boundary else None
    program_doc = program["doc"] if program else None
    if program_doc is None:
        raise ProblemError(400, "Project has no program graph to critique against")

    adjustments = critic.propose_adjustments(body.feedback, program_doc)
    new_program = critic.apply_adjustments(program_doc, adjustments)

    # Use a fresh seed for the regenerated plan: the generator is a deterministic function of
    # (boundary, program, seed), so reusing the parent's seed with only the program adjusted
    # tends to reproduce a near-identical layout. A new seed lets the layout actually change.
    # Generate several candidates and keep the one that best satisfies the adjusted program
    # (highest weighted-adjacency score) — a single regeneration often doesn't actually achieve
    # the requested adjacency even though the layout changes.
    base_seed = (parent.get("seed") or 0) + random.randint(1, 1_000_000)
    docs = await _candidate_plans(boundary_doc, new_program, 6, base_seed, project_id)
    new_doc = _pick_best_candidate(docs)
    new_doc["id"] = oid()
    new_doc["project_id"] = project_id
    new_doc["parent_plan_id"] = parent["_id"]
    assert_document("plan.schema.json", new_doc)

    ruleset_doc = await _load_ruleset(db, project_id)
    layout_score = new_doc.get("score")
    validation = await _validate_plan(new_doc, ruleset_doc) if ruleset_doc else None
    score = validation["score"] if validation else layout_score

    row = {
        "_id": new_doc["id"],
        "project_id": project_id,
        "parent_plan_id": parent["_id"],
        "source": "critique",
        "seed": new_doc.get("seed", base_seed),
        "score": score,
        "layout_score": layout_score,
        "validation": validation,
        "doc": new_doc,
        "created_at": utcnow(),
    }
    await db[PLANS].insert_one(row)
    await db[PROJECTS].update_one(
        {"_id": project_id}, {"$set": {"current_plan_id": row["_id"]}}
    )
    out: dict[str, Any] = serialize(row)  # type: ignore[assignment]
    return {**out, "notes": adjustments["notes"], "adjustments": adjustments}


@router.get("/plans/{plan_a}/diff/{plan_b}", response_model=DiffOut)
async def diff_plans(
    plan_a: uuid.UUID,
    plan_b: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DiffOut:
    a = await _load(db, str(plan_a))
    b = await _load(db, str(plan_b))
    await authorize_project(db, a["project_id"], user)
    if a["project_id"] != b["project_id"]:
        raise ProblemError(400, "Plans belong to different projects")
    return DiffOut(**diff_docs(a["doc"], b["doc"]))
