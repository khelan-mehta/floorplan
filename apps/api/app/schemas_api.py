"""Pydantic request/response models for the API surface (distinct from domain JSON documents)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# --- auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    org_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str


# --- projects ---
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    units: str = "m"
    jurisdiction_id: str | None = None
    org_id: uuid.UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    units: str | None = None
    jurisdiction_id: str | None = None
    current_plan_id: uuid.UUID | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    units: str
    jurisdiction_id: str | None
    boundary_id: uuid.UUID | None
    program_id: uuid.UUID | None
    current_plan_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- plans ---
class PlanPatch(BaseModel):
    patch: dict[str, Any] = Field(default_factory=dict)
    source: str = "edited"


class PlanOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    parent_plan_id: uuid.UUID | None
    source: str
    seed: int | None
    score: float | None
    layout_score: float | None = None
    validation: dict[str, Any] | None = None
    doc: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class DiffOut(BaseModel):
    added: dict[str, Any]
    removed: dict[str, Any]
    changed: dict[str, Any]


class CritiqueRequest(BaseModel):
    feedback: str = Field(min_length=1)


class CritiqueOut(PlanOut):
    notes: str
    adjustments: dict[str, Any]


# --- jobs ---
class GenerateRequest(BaseModel):
    count: int = Field(default=4, ge=1, le=24)
    seed: int | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class JobOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    progress: float
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- collaboration / approval (Phase 17) ---
class ShareCreate(BaseModel):
    role: str = "client"


class ShareOut(BaseModel):
    id: uuid.UUID
    token: str
    role: str
    url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    body: str = Field(min_length=1)
    plan_id: uuid.UUID | None = None
    anchor: dict[str, Any] = Field(default_factory=dict)
    author_name: str | None = None


class CommentOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    plan_id: uuid.UUID | None
    author: str
    body: str
    anchor: dict[str, Any]
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalUpdate(BaseModel):
    plan_id: uuid.UUID
    state: str
    note: str | None = None


class ApprovalOut(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    state: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditOut(BaseModel):
    id: uuid.UUID
    action: str
    actor: str
    meta: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
