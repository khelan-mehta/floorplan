# Phase 03 — Backend Core & Persistence

**Goal:** A working API gateway with authentication, the data model persisted in Postgres,
project/boundary/program/plan CRUD, version lineage, and an async job queue + WebSocket progress
channel that later services (generator, export) plug into.

**Depends on:** Phases 01–02.

---

## Tasks

1. **Database layer**
   - SQLAlchemy 2.0 (async) + Alembic migrations in `infra/migrations`.
   - Tables: `users`, `projects`, `boundaries`, `program_graphs`, `plans`, `plan_versions`,
     `rule_sets`, `validation_reports`, `jobs`, `artifacts`, `memberships`.
   - Store large vector docs (`Plan`, `Boundary`, `ProgramGraph`) as **JSONB**, validated against
     Phase 02 schemas on write. Index `project_id`, `parent_plan_id`, `created_at`.
   - Enable **PostGIS**; store a derived `geometry(Polygon)` column for boundary outlines for
     spatial queries (area, bbox, contains) without re-parsing JSON.

2. **Auth & tenancy**
   - JWT access/refresh (or session cookies). Email/password + OAuth (Google) optional.
   - Org/workspace model with `memberships(role: owner|editor|viewer|client)`.
   - Row-level authorization helper enforced in every endpoint; `client` role is read+comment only.

3. **CRUD endpoints** (FastAPI routers, all payloads = Phase 02 types)
   - `POST/GET/PATCH/DELETE /projects`
   - `PUT /projects/{id}/boundary`, `GET .../boundary`
   - `PUT /projects/{id}/program`, `GET .../program`
   - `POST /projects/{id}/program/import` (multipart: area-program `.xlsx/.csv` → parse, map, return
     a preview/diff; commit creates/reconciles the `ProgramGraph`), `GET .../program/export.xlsx`,
     `GET /program/template.xlsx`, and import-profile CRUD (`/program/import-profiles`)
   - `GET /projects/{id}/plans`, `GET /plans/{id}`, `PATCH /plans/{id}` (creates a new version),
     `POST /plans/{id}/duplicate`, `GET /plans/{id}/versions`
   - `GET /codes?jurisdiction=`, `GET /rulesets/{id}` (read; populated by Phase 07)
   - Validate request bodies against JSON Schema; return RFC-7807 problem+json on error.

4. **Versioning**
   - Every `PATCH /plans/{id}` writes a **new immutable Plan** with `parent_plan_id` set; the
     project's "current" pointer moves. Never mutate a stored plan in place.
   - Expose a lineage/history endpoint and a diff endpoint (`GET /plans/{a}/diff/{b}`).

5. **Job queue + progress**
   - Arq (async) workers backed by Redis. Job types: `generate`, `validate`, `solidify`, `export`,
     `ingest_codes`. Jobs are **idempotent** keyed by inputs-hash (see `00 §7`).
   - `POST /projects/{id}/generate` enqueues and returns a `job_id`.
   - `GET /jobs/{id}` returns status; **WebSocket `/ws/jobs/{id}`** streams progress + final result.
   - Artifacts (glTF/DXF/IFC) saved to object storage; DB stores `artifacts` rows with URLs.

6. **Service client layer**
   - Internal typed HTTP clients from `api` → `generator`/`codes`/`validator`/`geometry`/`export`,
     with timeouts, retries, and circuit-breaking. Keep service URLs in typed settings.

7. **Observability & errors**
   - Request logging with correlation IDs, OpenTelemetry traces spanning api→worker→service,
     consistent error envelope, and a `/metrics` endpoint.

---

## Deliverables

- Migrations create the full schema; `make dev` + seed script yields a demo user + project.
- OpenAPI at `/docs` reflects all endpoints with Phase 02 types.
- A generated **typed TS API client** (from OpenAPI) published to `packages/` for the web app.
- End-to-end: create project → set boundary → set program → enqueue a stub `generate` job →
  receive progress over WebSocket → fetch resulting (stub) plan.

## Acceptance criteria

- Authorization: a `viewer` cannot PATCH; a `client` can only read/comment; cross-org access 403s.
- Plan edit creates a new version; history and diff endpoints work; original is unchanged.
- Re-enqueuing an identical `generate` job returns the cached result (idempotency proven by test).
- WebSocket delivers ≥3 progress events then a final result for the stub job.

## Sources

- FastAPI: https://fastapi.tiangolo.com/  · SQLAlchemy 2.0: https://docs.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/  · Arq: https://arq-docs.helpmanual.io/
- PostGIS: https://postgis.net/  · RFC 7807 problem details: https://datatracker.ietf.org/doc/html/rfc7807
- openapi-typescript: https://github.com/openapi-ts/openapi-typescript

---

## Claude build prompt

> Implement Phase 03 (Backend Core & Persistence) per `plan/phase-03-backend-core.md` in
> `apps/api` plus `services/worker`. Use FastAPI + async SQLAlchemy 2.0 + Alembic with Postgres
> (PostGIS enabled). Create tables for users, projects, boundaries, program_graphs, plans,
> plan_versions, rule_sets, validation_reports, jobs, artifacts, memberships; store Plan/Boundary/
> ProgramGraph as JSONB validated against the Phase 02 schemas on write, with a derived PostGIS
> geometry column for boundary outlines. Add JWT auth, an org/membership model with roles
> (owner/editor/viewer/client) and a row-level authorization helper (client = read+comment only).
> Implement CRUD for projects/boundary/program/plans/codes with RFC-7807 errors. Make every plan
> PATCH create a new immutable versioned Plan with parent lineage, plus history and diff endpoints.
> Add an Arq + Redis job queue (generate/validate/solidify/export/ingest_codes) with inputs-hash
> idempotency, a `POST /projects/{id}/generate` that enqueues a stub job, `GET /jobs/{id}`, and a
> WebSocket `/ws/jobs/{id}` that streams progress and the final result; persist artifacts to MinIO.
> Add typed internal HTTP clients to the other services (timeouts/retries), OpenTelemetry tracing,
> correlation IDs, and `/metrics`. Generate a typed TypeScript API client from OpenAPI into
> `packages/`. Provide a seed script and tests proving authorization, versioning, idempotency, and
> WebSocket progress.
