# 00 — Architecture, Stack & Repository Layout

This document is the contract every later phase assumes. Read it before any build phase.

---

## 1. Problem statement (from the brief)

Architects currently spend **months** producing floor-plan options that (a) fit a fixed building
outline, (b) satisfy **local building codes**, and (c) contain a required **set of rooms** with
desired **adjacencies**. Options go to the client; the approved one continues in **Revit**.

We are building a tool that compresses that to minutes:

1. **Input** the outer floor geometry (boundary, levels).
2. **Input** the **program**: an **area-programming spreadsheet (Excel)** and/or a **room
   adjacency graph** — which rooms/spaces are wanted, their quantities, target sizes, departments,
   and adjacencies (two interchangeable views of one model).
3. **Input/Select** the applicable **building code** (ingested and RAG-indexed).
4. **Generate** multiple creative, code-aware 3D floor-plan options inside that space.
5. **Edit** in the browser: swap room types, move walls, place/swap interior components.
6. **Export** to DWG (2D drawings) and IFC (BIM) for Revit to continue.

---

## 2. System decomposition (services)

| Service | Responsibility | Language/Runtime |
|---------|----------------|------------------|
| `web` | Browser SPA: editors, 2D canvas, 3D viewport, approval UI | TypeScript, React, R3F |
| `api` | Gateway: auth, projects, versions, orchestration, job dispatch | Python, FastAPI |
| `generator` | Graph + boundary → room layout candidates | Python, PyTorch + solver |
| `codes` | Building-code ingestion + RAG + rule extraction | Python, FastAPI + vector DB |
| `validator` | Score a plan against extracted rule objects | Python (pure, deterministic) |
| `geometry` | Solidify plan → 3D (walls/floors/openings), tessellate to glTF | Python (shapely/pygltflib) or TS |
| `export` | Plan/3D → DXF/DWG (ODA) and IFC4 | Python (ezdxf + ifcopenshell) |
| `worker` | Long jobs (generation, export, code ingest) off the request path | Python, queue consumer |

Communication: REST (sync CRUD) + a **job queue** (async generation/export) + **WebSocket** for
progress streaming. All payloads conform to the Phase 2 schemas.

> Keep `validator` and `geometry` **pure and deterministic** (same input → same output). They are
> the most testable parts and the foundation of trust; never put network calls or randomness in them.

---

## 3. Data flow (happy path)

```
1. User draws boundary  ──────────────►  api: POST /projects/:id/boundary
2a. User uploads area-program Excel ──►  api: POST /projects/:id/program/import  (parse+map→ProgramGraph)
2b. User edits program graph/grid ────►  api: PUT  /projects/:id/program
3. User picks jurisdiction ───────────►  codes: GET /codes?jurisdiction=...  (rule set id)
4. User clicks "Generate N options" ──►  api: POST /projects/:id/generate  (enqueues job)
        worker → generator: layouts (graph+boundary+ruleset) → K candidate Plans
        worker → validator: score each Plan → violations[] + score
        worker → geometry:  solidify top Plans → 3D + glTF
   ◄── WebSocket progress + results: Plan[] with scores
5. User edits a Plan ─────────────────►  api: PATCH /plans/:id  (re-validate on change)
6. User exports chosen Plan ──────────►  export: POST /plans/:id/export?format=dwg|ifc
7. Architect opens IFC/DWG in Revit.
```

---

## 4. The core model (canonical, defined fully in Phase 2)

Everything is a typed JSON document, versioned, and validated by JSON Schema on both ends.

- **Project** — owns boundary, program, generated plans, versions, members.
- **Boundary** — outer polygon(s) per level, site setback lines, north angle, units.
- **ProgramGraph** — nodes = required rooms (type, min/target area, constraints);
  edges = adjacency/connection requirements (adjacent, connected-by-door, no-direct-access).
- **Plan** — the generated/edited result: `level[] → room[] (polygon, type, area) →
  wall[] (segments, thickness) → opening[] (door/window) → fixture[]/furniture[]`.
- **RuleSet** — machine-checkable building-code rules extracted by the `codes` service.
- **ValidationReport** — per-Plan score + list of `{rule, status, message, geometry-ref}`.

Units: store everything in **millimetres** as integers where possible to avoid float drift;
present in m/ft per user preference. Coordinate system: project-local, +X east, +Y north,
+Z up, origin at boundary bounding-box min.

---

## 5. Tech stack (decisions + rationale)

### Frontend (`web`)
- **React 18 + TypeScript + Vite** — standard, fast HMR.
- **React Three Fiber + drei + three.js** — declarative 3D viewport. (r3f.docs.pmnd.rs)
- **2D editor**: HTML Canvas via **Konva** (react-konva) or a custom SVG layer — vector,
  snapping, dimension lines. Prefer Konva for hit-testing + transforms.
- **State**: **Zustand** (local/editor state) + **TanStack Query** (server cache).
- **Geometry in browser**: `three`, `three-bvh-csg` (booleans), `web-ifc` (IFC), `@thatopen/components`.
- **Styling/UI**: Tailwind + Radix UI primitives; **Tldraw**-style infinite canvas optional.

### Backend (`api`, `worker`, services)
- **Python 3.12 + FastAPI + Pydantic v2** — schema-first, async, OpenAPI for typed clients.
- **PostgreSQL + PostGIS** — projects, versions, and geometry queries; **JSONB** for plan docs.
- **Redis** — cache + queue broker; **RQ** or **Celery** or **Arq** for jobs (pick Arq: async-native).
- **Object storage** — S3-compatible (MinIO in dev) for glTF, DXF/DWG, IFC artifacts.
- **Geometry**: **shapely** (2D ops), **pyclipper** (offsetting/insetting walls),
  **mapbox-earcut/triangle** (triangulation), **pygltflib/trimesh** (3D + glTF).
- **ML**: **PyTorch**; layout model based on Graph2Plan/House-GAN++/HouseDiffusion lineage.
- **Solver fallback**: **OR-Tools** (CP-SAT) / **rectpack** for deterministic rectilinear packing.

### Codes / RAG (`codes`)
- **Vector DB**: **Qdrant** (self-host, simple) or pgvector to avoid an extra service.
- **Embeddings + extraction**: Claude API (Anthropic SDK) for rule extraction + an embedding model.
- **Doc parsing**: `unstructured` / `pymupdf` for PDFs of code documents.

### Export (`export`)
- **ezdxf** (DXF) + **ODA File Converter** add-on for DXF→DWG. (ezdxf.readthedocs.io)
- **IfcOpenShell** (`ifcopenshell`) for IFC4 authoring. (ifcopenshell.org)

### Infra
- **Docker + docker-compose** (dev), **Kubernetes** or a PaaS (Render/Fly/AWS ECS) for prod.
- **GPU worker pool** for the ML generator (autoscaled, separate from CPU workers).
- **Observability**: OpenTelemetry traces, Prometheus/Grafana, structured logs, Sentry.

> **Why Python backend + TS frontend split?** The generative/geometry/BIM ecosystems
> (PyTorch, shapely, ifcopenshell, ezdxf) are Python-first; the 3D/IFC web-viewing ecosystem
> (three.js, web-ifc, ThatOpen) is TS-first. We use each where it is strongest.

---

## 6. Repository layout (monorepo)

```
floorplangenerator/
├─ plan/                      # ← this playbook
├─ apps/
│  ├─ web/                    # React SPA (Vite)
│  └─ api/                    # FastAPI gateway
├─ services/
│  ├─ generator/             # ML + solver layout engine
│  ├─ codes/                 # RAG + rule extraction
│  ├─ validator/             # pure rule checker (importable lib + thin service)
│  ├─ geometry/              # solidify + tessellate
│  └─ export/                # DXF/DWG/IFC
├─ packages/
│  ├─ schemas/              # JSON Schemas + generated TS & Python types (source of truth)
│  ├─ ui/                    # shared React components
│  └─ geometry-core/         # shared TS geometry helpers (mirror of py where needed)
├─ infra/
│  ├─ docker-compose.yml      # dev stack: postgres, redis, minio, qdrant, oda
│  ├─ k8s/                    # prod manifests / helm
│  └─ migrations/             # alembic
├─ datasets/                  # RPLAN-derived training data (gitignored, doc'd how to fetch)
├─ models/                    # trained weights (DVC/LFS pointers)
├─ tests/                     # cross-service e2e + golden files
├─ .github/workflows/         # CI
└─ README.md
```

Tooling: **pnpm workspaces** (JS) + **uv**/**Poetry** (Python) + **Turborepo** or **Make** as the
task runner. One `make dev` brings up the full stack via docker-compose.

---

## 7. Cross-cutting contracts (must hold across all phases)

1. **Schema-first.** Edit JSON Schema in `packages/schemas` → codegen Pydantic + TS types.
   No service hand-rolls a payload shape.
2. **Units & coordinates** as in §4. Validate on ingest; reject ambiguous units.
3. **Idempotent jobs.** Generation/export jobs are keyed by `(inputs hash)`; re-runs return cached.
4. **Everything versioned.** A Plan edit creates a new immutable Plan version; projects keep history.
5. **Determinism boundaries.** `validator`, `geometry`, `export` are deterministic; `generator`
   takes an explicit `seed`. Record the seed with every result for reproducibility.
6. **No secrets in code.** Config via env + a typed settings object per service.

---

## 8. Milestones (suggested grouping of phases)

- **M1 — Skeleton (Phases 1–4):** repo, schemas, backend CRUD, frontend shell. *Demo: create a project.*
- **M2 — Inputs (Phases 5–7):** boundary editor, program graph, code RAG. *Demo: define a problem.*
- **M3 — Generation (Phases 8–9):** layout engine + validator. *Demo: get scored plans (2D).*
- **M4 — Visual & edit (Phases 10–13):** 2D editor, 3D, component library, interactive editing.
- **M5 — Deliverables (Phases 14–16):** variants, DWG/IFC export, Revit roundtrip.
- **M6 — Product (Phases 17–20):** approval workflow, deploy/scale, testing, hardening.

> A thin **vertical slice** (boundary → trivial solver → 2D → DXF) across M1–M5 *before* investing
> in the ML generator de-risks the hardest integration (export/Revit) early. Each phase notes where
> a stub keeps the slice moving.
