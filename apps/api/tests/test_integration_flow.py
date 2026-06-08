"""End-to-end happy path against a real Postgres/PostGIS.

Gated behind FPG_DB_TESTS=1 with DATABASE_URL pointing at a PostGIS database (the api reads it at
import). Not wired into CI yet (needs a validated PostGIS service) — run locally/in a follow-up job:

    FPG_DB_TESTS=1 DATABASE_URL=postgresql+asyncpg://fpg:fpg@localhost:5432/fpg \
        uv run pytest tests/test_integration_flow.py -q
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("FPG_DB_TESTS") != "1", reason="requires a Postgres/PostGIS database"
)

EXAMPLES = Path(__file__).resolve().parents[3] / "packages" / "schemas" / "examples"


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from app.db import Base, engine

    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _poll_job(client: httpx.AsyncClient, job_id: str, headers: dict) -> dict:
    for _ in range(50):
        res = await client.get(f"/jobs/{job_id}", headers=headers)
        body = res.json()
        if body["status"] in {"succeeded", "failed"}:
            return body
    raise AssertionError("job did not finish")


async def test_full_flow(client: httpx.AsyncClient) -> None:
    reg = await client.post(
        "/auth/register",
        json={"email": "a@b.com", "password": "password123", "name": "A"},
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    proj = await client.post("/projects", json={"name": "P", "units": "m"}, headers=headers)
    assert proj.status_code == 201, proj.text
    pid = proj.json()["id"]

    boundary = json.loads((EXAMPLES / "boundary-rect.example.json").read_text())
    rb = await client.put(f"/projects/{pid}/boundary", json=boundary, headers=headers)
    assert rb.status_code == 200, rb.text

    program = json.loads((EXAMPLES / "program-2bed.example.json").read_text())
    rp = await client.put(f"/projects/{pid}/program", json=program, headers=headers)
    assert rp.status_code == 200, rp.text

    gen = await client.post(
        f"/projects/{pid}/generate", json={"count": 3, "seed": 1}, headers=headers
    )
    assert gen.status_code == 202, gen.text
    job = await _poll_job(client, gen.json()["id"], headers)
    assert job["status"] == "succeeded"
    assert len(job["result"]["plan_ids"]) == 3

    # idempotency: same inputs return the cached job
    gen2 = await client.post(
        f"/projects/{pid}/generate", json={"count": 3, "seed": 1}, headers=headers
    )
    assert gen2.json()["id"] == gen.json()["id"]

    plans = await client.get(f"/projects/{pid}/plans", headers=headers)
    assert len(plans.json()) == 3
    plan_id = plans.json()[0]["id"]

    # editing creates a new immutable version
    patched = await client.patch(
        f"/plans/{plan_id}", json={"patch": {"score": 77.0}, "source": "edited"}, headers=headers
    )
    assert patched.status_code == 200
    new_id = patched.json()["id"]
    assert new_id != plan_id
    assert patched.json()["parent_plan_id"] == plan_id

    diff = await client.get(f"/plans/{plan_id}/diff/{new_id}", headers=headers)
    assert "/score" in diff.json()["changed"] or "score" in str(diff.json())
