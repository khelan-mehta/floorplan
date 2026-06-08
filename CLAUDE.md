# CLAUDE.md — Generative 3D Floor Plan Studio

> Always-loaded orientation for any Claude session in this repo. Keep it short and current.

## What this is
A web tool that generates **code-compliant 3D floor plans** inside a user-supplied building outline,
driven by an **area-programming spreadsheet (Excel)** and/or a **room adjacency graph**, constrained
by **local building codes** (RAG-ingested), with in-browser editing and **DWG/IFC export for Revit**.

## Where the plan lives (read before building)
- `plan/README.md` — phase index + how to use.
- `plan/00-architecture-and-stack.md` — **the contract**: services, data flow, stack, repo layout.
- `plan/phase-NN-*.md` — one elaborate, paste-ready build prompt per phase.
- `plan/PROGRESS.md` — current status, deviations, follow-ups. **Update this at each phase boundary.**

## Golden rules (the cross-cutting contracts)
1. **Schema-first.** `packages/schemas` is the single source of truth. Edit schema → `pnpm codegen`
   → both Python (Pydantic) and TS types regenerate. No service hand-rolls a payload shape.
2. **Units & coordinates.** Store geometry as **integer millimetres**; +X east, +Y north, +Z up,
   origin at boundary bbox-min. Display units are presentation-only.
3. **Generator proposes, validator disposes.** Generation and code-compliance are separate services.
   `validator`, `geometry`, `export` are **pure & deterministic** — no network, no randomness.
4. **Everything versioned.** A plan edit creates a new immutable Plan version; never mutate in place.
5. **Idempotent jobs**, keyed by inputs-hash. The generator takes an explicit `seed`; record it.

## Stack
- **Frontend** (`apps/web`): React 18 + TS (strict) + Vite + React-Three-Fiber + Konva + Zustand + TanStack Query.
- **Backend** (`apps/api` + `services/*`): Python 3.12 + FastAPI + Pydantic v2; **MongoDB (Motor)**, Redis/Arq, MinIO (S3), Qdrant.
  (DB was swapped from Postgres/PostGIS to MongoDB — domain docs are JSON; see memory `use-mongodb-not-postgres`.)
- **Generator**: PyTorch (Graph2Plan/House-GAN++ lineage) + OR-Tools solver. **Export**: ezdxf (+ODA) + ifcopenshell.

## Repo layout
`apps/{web,api}` · `services/{generator,codes,validator,geometry,export}` ·
`packages/{schemas,ui,geometry-core}` · `infra/` · `plan/` · `tests/`

## Commands (this machine: node, docker CLI, git; pnpm global; Python 3.12 via winget)
- `pnpm` is installed globally — use `pnpm <cmd>` directly. Canonical task runner is the root
  `package.json` scripts (cross-platform), not `make`:
  - `pnpm install` · `pnpm dev` (dockerized stack) · `pnpm dev:web` (Vite only)
  - `pnpm lint` / `typecheck` / `test` / `format` / `build` / `codegen`
- **Python 3.12** at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`; each Python project has a
  gitignored `.venv`. Run a backend suite: `cd <svc>; .\.venv\Scripts\python.exe -m pytest -q`
  (also `-m ruff check .`, `-m mypy app`). CI runs ruff/mypy/pytest per service dir, so each Python
  `pyproject.toml` carries its own `[tool.mypy]` ignore-missing-imports for untyped libs.
- **Docker daemon is usually OFF** here → full stack + Postgres integration/e2e can't run locally;
  unit suites do. Start Docker Desktop for `pnpm dev`.

## Conventions
- TS: strict, no `any` in app code; consume only generated schema types + the generated API client.
- Python: Ruff (lint+format) + mypy strict; FastAPI routers thin, logic in pure modules.
- Commits: small, per concern. Branch off `main`; don't commit secrets (use `.env`, see `.env.example`).

## Compliance note
Code-compliance output is **decision-support, not legal sign-off**. Every rule keeps a citation;
every export carries a disclaimer + ruleset version + validation score.
