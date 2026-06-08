"""Enums + collection names for the MongoDB data layer. Documents are plain dicts (validated
against the Phase-02 JSON Schemas on write); there is no ORM."""

from __future__ import annotations

import enum


class Role(enum.StrEnum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"
    client = "client"


class JobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


# Collection names
USERS = "users"
ORGS = "orgs"
MEMBERSHIPS = "memberships"
PROJECTS = "projects"
BOUNDARIES = "boundaries"
PROGRAM_GRAPHS = "program_graphs"
PLANS = "plans"
RULE_SETS = "rule_sets"
JOBS = "jobs"
SHARES = "shares"
COMMENTS = "comments"
APPROVALS = "approvals"
AUDIT_LOG = "audit_log"
