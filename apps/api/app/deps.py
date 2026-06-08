"""Auth + authorization dependencies (row-level, role-aware) over MongoDB."""

from __future__ import annotations

from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from .db import get_db, serialize
from .errors import ProblemError
from .models import MEMBERSHIPS, PROJECTS, USERS, Role
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)

WRITE_ROLES = {Role.owner, Role.editor}
COMMENT_ROLES = {Role.owner, Role.editor, Role.client}


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    if creds is None:
        raise ProblemError(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except jwt.PyJWTError as exc:
        raise ProblemError(401, "Invalid token", str(exc)) from exc
    user = await db[USERS].find_one({"_id": str(payload.get("sub"))})
    if user is None:
        raise ProblemError(401, "User not found")
    return serialize(user)  # type: ignore[return-value]


async def get_role_in_org(db: AsyncIOMotorDatabase, org_id: str, user_id: str) -> Role | None:
    membership = await db[MEMBERSHIPS].find_one({"org_id": org_id, "user_id": user_id})
    return Role(membership["role"]) if membership else None


async def authorize_project(
    db: AsyncIOMotorDatabase,
    project_id: str,
    user: dict[str, Any],
    *,
    write: bool = False,
    comment: bool = False,
) -> tuple[dict[str, Any], Role]:
    """Load a project and verify the user's role permits the requested access."""
    project = await db[PROJECTS].find_one({"_id": project_id})
    if project is None:
        raise ProblemError(404, "Project not found")
    role = await get_role_in_org(db, project["org_id"], user["id"])
    if role is None:
        raise ProblemError(403, "Not a member of this project's organization")
    if write and role not in WRITE_ROLES:
        raise ProblemError(403, "Insufficient role", f"{role.value} cannot modify this resource")
    if comment and role not in COMMENT_ROLES:
        raise ProblemError(403, "Insufficient role", f"{role.value} cannot comment")
    return serialize(project), role  # type: ignore[return-value]
