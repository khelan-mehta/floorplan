# Generative 3D Floor Plan Studio

Generate **code-compliant 3D floor plans** inside a user-supplied building outline, driven by an
**area-programming spreadsheet (Excel)** and a **room adjacency graph**, constrained by **local
building codes** (RAG-ingested). Edit rooms and interiors in the browser, then **export to DWG/IFC**
for Autodesk Revit.

> 📋 The full implementation plan lives in [`plan/`](plan/README.md) (20 phases).
> 🧭 Project orientation for contributors/agents is in [`CLAUDE.md`](CLAUDE.md).
> ✅ Current status is tracked in [`plan/PROGRESS.md`](plan/PROGRESS.md).

This repository is currently at **Phase 01 — Foundations** (the skeleton).

---

## Prerequisites

- **Docker Desktop** (runs the whole stack, including the Python services — no local Python needed).
- **Node.js ≥ 20** with **corepack** (ships with Node) for the web app + tooling.
- *(Optional, for native Python work)* **Python 3.12** + [`uv`](https://docs.astral.sh/uv/).

> This repo uses **pnpm** via corepack. If `pnpm` isn't on your PATH, prefix commands with
> `corepack ` (e.g. `corepack pnpm install`), or run `corepack enable` once (may need admin on Windows).

## Quick start

```bash
# 1. Configure environment
cp .env.example .env

# 2. Install JS dependencies
corepack pnpm install

# 3a. Run the whole dockerized stack (web + api + services + postgres/redis/minio/qdrant)
corepack pnpm dev
#    web → http://localhost:5173    api docs → http://localhost:8000/docs

# 3b. …or run just the web app locally (expects an API at VITE_API_BASE_URL)
corepack pnpm dev:web
```

When the stack is up, the web app's status panel turns **green** once it reaches the API `/health`.

## Common tasks

| Task | Command (cross-platform) |
|------|--------------------------|
| Install JS deps | `corepack pnpm install` |
| Full dev stack | `corepack pnpm dev` |
| Web only | `corepack pnpm dev:web` |
| Lint | `corepack pnpm lint` |
| Typecheck | `corepack pnpm typecheck` |
| Test | `corepack pnpm test` |
| Format | `corepack pnpm format` |

Unix users can use the `Makefile` (`make dev`, `make lint`, …) if `make` is installed.

## Ports

| Service | URL |
|---------|-----|
| web | http://localhost:5173 |
| api | http://localhost:8000 (`/docs`, `/health`, `/version`) |
| generator / codes / validator / geometry / export | :8001 / :8002 / :8003 / :8004 / :8005 |
| postgres | :5432 · redis :6379 · minio :9000 (console :9001) · qdrant :6333 |

## Repository layout

```
apps/         web (React/Vite) + api (FastAPI gateway)
services/     generator · codes · validator · geometry · export  (FastAPI, run via Docker)
packages/     schemas (source of truth) · ui · geometry-core
infra/        docker-compose dev stack + migrations
plan/         the 20-phase implementation playbook
datasets/     RPLAN fetch docs (not committed)  ·  models/  trained weights (not committed)
tests/        cross-service e2e + golden files (Phase 19)
```

## License & compliance

Code-compliance output is **decision-support, not a legal guarantee**. A licensed professional must
review every plan. See `plan/phase-07` and `plan/phase-20` for the disclaimer + citation policy.
