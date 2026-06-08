# Phase 01 — Foundations & Tooling

**Goal:** Stand up the monorepo, dev tooling, CI, and a one-command local stack so every later
phase has a consistent home. No product features yet — this is the ground everything stands on.

**Depends on:** `00-architecture-and-stack.md` (repo layout, stack decisions).

---

## Tasks

1. **Monorepo scaffolding**
   - Initialize git. Create the directory tree from `00 §6`.
   - JS workspace: `pnpm-workspace.yaml` covering `apps/web`, `packages/*`.
   - Python workspace: `uv` (preferred) or Poetry; one virtualenv strategy, shared `ruff`/`mypy`
     config at root. Each Python service has its own `pyproject.toml` but inherits root lint config.
   - Root task runner: `Makefile` (or Turborepo `turbo.json`) with `make dev`, `make test`,
     `make lint`, `make fmt`, `make typecheck`, `make codegen`.

2. **Linting / formatting / types**
   - JS: ESLint + Prettier + TypeScript strict mode.
   - Python: Ruff (lint+format) + mypy strict + Pydantic plugin.
   - Pre-commit hooks (`pre-commit`) running ruff, prettier, eslint, and schema validation.

3. **Dev stack (`infra/docker-compose.yml`)**
   - Services: `postgres` (with PostGIS), `redis`, `minio` (S3), `qdrant` (vector DB),
     `oda-file-converter` (or document its host install), plus app containers.
   - Healthchecks + named volumes. `.env.example` documenting every variable.
   - `make dev` → `docker compose up` brings the full stack up with hot reload.

4. **CI (`.github/workflows`)**
   - Jobs: lint, typecheck, unit tests (JS + Py), schema-codegen drift check, docker build.
   - Cache pnpm + uv. Fail PR if `make codegen` produces a diff (schemas out of sync).

5. **Baseline app shells (compile-only, no features)**
   - `apps/web`: Vite + React + TS "hello" that boots and shows app version + API health.
   - `apps/api`: FastAPI app with `/health` and `/version`; OpenAPI served at `/docs`.
   - Each service (`generator`, `codes`, `validator`, `geometry`, `export`): minimal FastAPI app
     with `/health` so compose wiring is testable.

6. **Secrets & config**
   - Typed settings object per service (Pydantic `BaseSettings` / Vite env). No literals in code.
   - `direnv`/`.env` for local; document prod secret strategy (sealed secrets / SSM) as a TODO.

7. **Docs**
   - Root `README.md`: prerequisites, `make dev`, how to run tests, ports table.
   - `CONTRIBUTING.md`: branch naming, commit style, codegen workflow.

---

## Deliverables

- `make dev` brings up web + api + all stub services + infra; each `/health` returns 200.
- `make lint && make typecheck && make test` pass on a clean checkout.
- CI green on a trivial PR.

## Acceptance criteria

- A new contributor can clone, run `make dev`, and load the web app showing API health within
  one command (after Docker is installed).
- Pre-commit blocks a deliberately malformed file.
- CI fails when a schema is edited without running codegen.

## Sources

- pnpm workspaces: https://pnpm.io/workspaces
- uv (Python): https://docs.astral.sh/uv/
- Ruff: https://docs.astral.sh/ruff/
- FastAPI: https://fastapi.tiangolo.com/
- Vite: https://vitejs.dev/
- pre-commit: https://pre-commit.com/

---

## Claude build prompt

> Implement Phase 01 (Foundations & Tooling) for the Generative 3D Floor Plan Studio described in
> `plan/00-architecture-and-stack.md`. Create the monorepo layout from §6 with pnpm workspaces and
> a `uv`-managed Python multi-service setup. Add root-level Ruff/mypy/ESLint/Prettier configs in
> strict mode, pre-commit hooks, and a `Makefile` with `dev/test/lint/fmt/typecheck/codegen`
> targets. Write `infra/docker-compose.yml` with postgres+postgis, redis, minio, qdrant, and the
> ODA File Converter (document host install if no image), each with healthchecks and a documented
> `.env.example`. Scaffold compile-only app shells: `apps/web` (Vite+React+TS strict, shows app
> version and pings API `/health`), `apps/api` (FastAPI with `/health`, `/version`, OpenAPI), and
> minimal FastAPI `/health` stubs for `generator`, `codes`, `validator`, `geometry`, `export`.
> Add typed settings objects (no hard-coded config). Add a GitHub Actions CI workflow running
> lint, typecheck, unit tests, a schema-codegen drift check, and docker builds. Write the root
> README and CONTRIBUTING. Acceptance: `make dev` boots the full stack with all `/health` green,
> and `make lint && make typecheck && make test` pass clean. Do not implement product features yet.
