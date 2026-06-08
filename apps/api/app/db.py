"""MongoDB (Motor) data layer.

Document-oriented persistence — a natural fit since boundary/program/plan are JSON documents.
Each document uses a string-UUID `_id`; `serialize()` renames it to `id` for API responses.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .settings import settings

client: AsyncIOMotorClient = AsyncIOMotorClient(settings.mongodb_uri, uuidRepresentation="standard")
db: AsyncIOMotorDatabase = client[settings.mongodb_db]


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency — returns the shared database handle."""
    return db


def oid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


def serialize(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Rename Mongo `_id` -> `id` for API responses."""
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = out.pop("_id")
    return out


async def ensure_indexes() -> None:
    await db["users"].create_index("email", unique=True)
    await db["memberships"].create_index([("org_id", 1), ("user_id", 1)], unique=True)
    await db["projects"].create_index("org_id")
    await db["plans"].create_index("project_id")
    await db["jobs"].create_index("inputs_hash")
    await db["shares"].create_index("token", unique=True)
