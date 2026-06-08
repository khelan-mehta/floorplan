"""End-to-end smoke for the building-code (Phase 07) compliance loop against a LIVE stack.

Not part of the unit suites (it needs the dockerized stack up + seeded). Run:

    docker compose -f infra/docker-compose.yml up -d --build
    docker compose -f infra/docker-compose.yml exec api python -m app.seed
    python tests/e2e_phase07.py            # uses stdlib only

It exercises: login -> project jurisdiction -> ask-the-code (citation) -> generate -> per-plan
compliance score + ValidationReport -> export (DXF/IFC/CSV).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("FPG_API", "http://localhost:8000")
EMAIL = os.environ.get("FPG_EMAIL", "demo@example.com")
PASSWORD = os.environ.get("FPG_PASSWORD", "demo-password")


def _req(method: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 - local dev URL
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        return exc.code, exc.read()


def jget(method: str, path: str, **kw: object) -> dict:
    status, raw = _req(method, path, **kw)  # type: ignore[arg-type]
    assert status < 400, f"{method} {path} -> {status}: {raw[:300]!r}"
    return json.loads(raw) if raw else {}


def main() -> int:
    print(f"API = {API}")
    token = jget("POST", "/auth/login", body={"email": EMAIL, "password": PASSWORD})["access_token"]
    print("✓ login")

    projects = jget("GET", "/projects", token=token)
    project = next((p for p in projects if p["name"] == "Demo 2-Bed Apartment"), projects[0])
    pid = project["id"]
    assert project["jurisdiction_id"], "demo project has no jurisdiction set"
    print(f"✓ project {pid!s} jurisdiction={project['jurisdiction_id']}")

    ask = jget(
        "POST",
        "/codes/query",
        token=token,
        body={"jurisdiction_id": project["jurisdiction_id"], "query": "minimum bedroom area?"},
    )
    top = ask["results"][0]
    assert top["section"] == "1208.1", f"expected §1208.1, got §{top['section']}"
    print(f"✓ ask-the-code: §{top['section']} {top['heading']!r}")

    job = jget("POST", f"/projects/{pid}/generate", token=token, body={"count": 6})
    for _ in range(60):
        job = jget("GET", f"/jobs/{job['id']}", token=token)
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(1)
    assert job["status"] == "succeeded", f"generate {job['status']}: {job.get('error')}"
    print(f"✓ generate: {len(job['result']['plan_ids'])} plans")

    plans = jget("GET", f"/projects/{pid}/plans", token=token)
    scored = [p for p in plans if p.get("validation")]
    assert scored, "no plan carried a ValidationReport — validator not wired?"
    best = max(scored, key=lambda p: p["score"] or 0)
    report = best["validation"]
    fails = [r for r in report["results"] if r["status"] == "fail"]
    print(
        f"✓ compliance: best score {best['score']} (layout {best.get('layout_score')}); "
        f"{len(fails)} flagged rules; ruleset {report['ruleset_id']}"
    )

    for fmt, minsize in (("dxf", 1000), ("ifc", 1000), ("csv", 50)):
        status, raw = _req("POST", f"/plans/{best['id']}/export?format={fmt}", token=token)
        assert status == 200 and len(raw) >= minsize, f"export {fmt} -> {status}, {len(raw)} bytes"
        print(f"✓ export {fmt}: {len(raw)} bytes")

    print("\nALL E2E CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
