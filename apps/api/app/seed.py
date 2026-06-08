"""Seed a demo org/user/project with a boundary + program (MongoDB). Idempotent.

Run with:  python -m app.seed   (with MONGODB_URI/MONGODB_DB pointing at a running mongod)
Login afterwards as demo@example.com / demo-password.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from .db import db, ensure_indexes, oid, utcnow
from .models import (
    BOUNDARIES,
    MEMBERSHIPS,
    ORGS,
    PROGRAM_GRAPHS,
    PROJECTS,
    RULE_SETS,
    USERS,
    Role,
)
from .security import hash_password

DEMO_EMAIL = "demo@example.com"
SEED_RULESET = "ruleset-generic-ibc.example.json"


def _examples_dir() -> Path:
    """Locate the schema example fixtures in both the repo and the Docker image layout."""
    env = os.environ.get("FPG_EXAMPLES_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    candidates = [
        *(p / "packages" / "schemas" / "examples" for p in here.parents),  # repo checkout
        Path("/app/examples"),  # bundled in the api Docker image
    ]
    return next((c for c in candidates if c.exists()), candidates[0])


EXAMPLES = _examples_dir()


async def _seed_ruleset() -> str:
    """Upsert the seed jurisdiction's published RuleSet (Phase 07) into Mongo. Returns its id."""
    doc = json.loads((EXAMPLES / SEED_RULESET).read_text(encoding="utf-8"))
    await db[RULE_SETS].update_one(
        {"_id": doc["id"]},
        {
            "$set": {
                "jurisdiction": doc["jurisdiction"],
                "version": doc["version"],
                "doc": doc,
                "updated_at": utcnow(),
            }
        },
        upsert=True,
    )
    return str(doc["id"])


async def seed() -> None:
    await ensure_indexes()
    ruleset_id = await _seed_ruleset()
    if await db[USERS].find_one({"email": DEMO_EMAIL}):
        print("Seed already present; ruleset refreshed; nothing else to do.")
        return

    now = utcnow()
    uid = oid()
    await db[USERS].insert_one(
        {
            "_id": uid,
            "email": DEMO_EMAIL,
            "name": "Demo User",
            "password_hash": hash_password("demo-password"),
            "created_at": now,
        }
    )
    org_id = oid()
    await db[ORGS].insert_one({"_id": org_id, "name": "Demo Studio", "created_at": now})
    await db[MEMBERSHIPS].insert_one(
        {"_id": oid(), "org_id": org_id, "user_id": uid, "role": Role.owner.value, "created_at": now}
    )

    project_id = oid()
    boundary_id = oid()
    program_id = oid()
    boundary_doc = json.loads((EXAMPLES / "boundary-rect.example.json").read_text())
    program_doc = json.loads((EXAMPLES / "program-2bed.example.json").read_text())

    await db[BOUNDARIES].insert_one(
        {"_id": boundary_id, "project_id": project_id, "doc": boundary_doc, "created_at": now}
    )
    await db[PROGRAM_GRAPHS].insert_one(
        {"_id": program_id, "project_id": project_id, "doc": program_doc, "created_at": now}
    )
    await db[PROJECTS].insert_one(
        {
            "_id": project_id,
            "org_id": org_id,
            "name": "Demo 2-Bed Apartment",
            "units": "m",
            "jurisdiction_id": ruleset_id,
            "boundary_id": boundary_id,
            "program_id": program_id,
            "current_plan_id": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    print(f"Seeded user={DEMO_EMAIL} (password demo-password) project={project_id}")


if __name__ == "__main__":
    asyncio.run(seed())
