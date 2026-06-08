from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..db import get_db, oid, utcnow
from ..deps import get_current_user
from ..errors import ProblemError
from ..models import MEMBERSHIPS, ORGS, USERS, Role
from ..schemas_api import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens(user_id: str) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)
) -> TokenResponse:
    if await db[USERS].find_one({"email": body.email}):
        raise ProblemError(409, "Email already registered")
    now = utcnow()
    uid = oid()
    await db[USERS].insert_one(
        {
            "_id": uid,
            "email": body.email,
            "name": body.name,
            "password_hash": hash_password(body.password),
            "created_at": now,
        }
    )
    org_id = oid()
    await db[ORGS].insert_one(
        {"_id": org_id, "name": body.org_name or f"{body.name}'s workspace", "created_at": now}
    )
    await db[MEMBERSHIPS].insert_one(
        {"_id": oid(), "org_id": org_id, "user_id": uid, "role": Role.owner.value, "created_at": now}
    )
    return _tokens(uid)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> TokenResponse:
    user = await db[USERS].find_one({"email": body.email})
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise ProblemError(401, "Invalid credentials")
    return _tokens(user["_id"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncIOMotorDatabase = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except jwt.PyJWTError as exc:
        raise ProblemError(401, "Invalid refresh token", str(exc)) from exc
    user = await db[USERS].find_one({"_id": str(payload.get("sub"))})
    if user is None:
        raise ProblemError(401, "User not found")
    return _tokens(user["_id"])


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)) -> dict:
    return user
