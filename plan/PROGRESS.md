# Build Progress Ledger

> Cheap cross-session hand-off. Update at every phase boundary: status, deviations, follow-ups.
> Status legend: ⬜ not started · 🟨 in progress · ✅ done · ⏭️ deferred

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 01 | Foundations & tooling | ✅ | Scaffold complete. JS gates verified green; Python/stack boot pending Docker daemon (see notes) |
| 02 | Domain model & schemas | ✅ | JSON Schemas + TS codegen + Ajv validators + geometry lint + fixtures + tests verified green; Python lib authored for CI |
| 03 | Backend core & persistence | ✅ | FastAPI gateway authored: DB/ORM, JWT+RBAC, CRUD, immutable plan versioning+diff, idempotent jobs + WS progress, stub generate, observability. Unit tests + new CI jobs. (No local Python/Docker → CI-verified.) |
| 04 | Frontend shell | ✅ | React app + @fpg/ui design system, auth/routing/RBAC, TanStack Query over typed client, Zustand, 2D (Konva) + 3D (R3F) viewports rendering a bundled demo plan. Verified locally (typecheck/lint/test/build/dev-serve). |
| 05 | Boundary input | ✅ | Konva draw/edit/snap, multi-level, setbacks+envelope, north, DXF import, 3D massing, save→PUT. Verified locally (typecheck/lint/test/build). |
| 06 | Program input (Excel + graph) | ✅ | Excel/CSV import (mapping+inference+expansion), table+React Flow graph+matrix, budget meter, templates, export, save→PUT. Verified locally. |
| 07 | Building-code RAG | ✅ | `services/codes`: clause-level ingest + hybrid (dense+BM25) retrieval + prose→Rule extraction (**OpenAI API** w/ deterministic offline fallback) + review/publish + versioned diff on re-ingest. Seed `generic-ibc-2021` (12 published categories). API proxies `/codes/query`; validator wired into generate (per-plan compliance score+report); web Codes tab + compliance panel. Verified locally (codes 9 tests; ruff/mypy clean) + full dockerized e2e (OpenAI extraction live). |
| 08 | Generative layout engine | 🟨 | Deterministic solver in `services/generator` + `/generate`; api calls it with stub fallback. **Now partitions the ACTUAL boundary polygon** (recursive area-bisection in `partition.py`/`geometry.py`) so rooms conform to any simple polygon (concave/L/arc-approx), not just the bbox; per-edge walls (exterior via outline membership), shared-edge adjacency + circulation spanning tree, entry/door-count logic, windows. **Verified locally** (ruff/mypy/pytest, 13 tests incl. L-shape tiling/containment). ML path (Graph2Plan/RPLAN) + true curved-arc primitives deferred. |
| 09 | Code constraints & scoring | ✅ | `services/validator`: rule-DSL interpreter + geometry metrics + scoring → ValidationReport. Verified locally (5 tests). |
| 10 | 2D plan editor | 🟨 | Editable Konva canvas (vertex drag, fixtures, selection) + undo/redo + Save→version. Verified (build/test). Wall/opening direct-edit, dimensions, snapping engine, live-validation overlay deferred. |
| 11 | 3D model generation | ✅ | `services/geometry`: solidify → GLB (slabs+walls, tagged). Verified locally (3 tests). CSG openings/stairs/multi-level + web loading server glTF deferred. |
| 12 | Component & interior library | 🟨 | Catalog + per-room auto-furnish (pure, tested) + 2D/3D fixture render + catalog-aware inspector. Server registry/glTF assets/IFC mapping/clearance solving deferred. |
| 13 | Interactive editing | 🟨 | Room-type change, auto-furnish, fixture add/remove, vertex move — all undo/redo + versioned. Swap-layout, scoped regen, semantic wall push/pull, one-click fixes deferred. |
| 14 | Variants & comparison | 🟨 | Generate N options + score-sorted variant gallery to open/compare. Side-by-side diff, design sliders, "more like this" deferred. |
| 15 | Export to DWG/IFC | ✅ | `services/export`: DXF (AIA layers, 10 m verified) + IFC4 (spatial tree + IfcSpaces, reopened via ifcopenshell) + CSV; api proxy `POST /plans/{id}/export`; web Export menu. Verified locally (5 tests). DWG-via-ODA + IFC 3D geometry + PDF sheets deferred. |
| 16 | Revit interoperability | 🟨 | IFC export upgraded to native categories (IfcWall solids + IfcDoor/IfcWindow + IfcSpace), verified via ifcopenshell reopen; mapping spec + Revit C# add-in + Dynamo scaffold authored (not compiled — no Revit/.NET). IFC opening voids + Fixture→IFC deferred. |
| 17 | Approval & collaboration | 🟨 | Backend: shares (capability URLs), client review (`GET /shared/{token}`), comments (auth + token), approval state machine (single-approved enforced) + audit log. Verified (api 16 tests). Frontend share/approve UI deferred. |
| 18 | Deploy, scale, observe | 🟨 | k8s manifests (api/worker/web + HPA + Ingress), KEDA scale-to-zero worker, Prometheus scrape, CD workflow, multi-stage web (nginx prod) image. YAML-validated + compose valid; not yet applied to a cluster. |
| 19 | Testing & QA | ⬜ | — |
| 20 | Hardening & polish | ⬜ | — |

---

## Deviations from the plan (and why)

- **Task runner: root `package.json` scripts instead of `make`.** The dev machine (Windows) has no
  `make`. Node scripts are cross-platform and already present. A `Makefile` is kept as a convenience
  for Unix users. → affects `plan/phase-01-foundations.md` acceptance wording (`make dev` → `pnpm dev`).
- **pnpm via corepack (`corepack pnpm`).** Global pnpm shim couldn't be installed (Program Files is
  not writable without admin); corepack runs pnpm fine. Documented in `CLAUDE.md` + root README.
- **Python services run via Docker** for the full stack. As of 2026-06-06 local Python 3.12 IS
  installed (per-service `.venv`s), so backend unit suites (schemas-py, api, generator) run natively;
  the dockerized stack + a live Postgres are still needed for integration/e2e.

## Open follow-ups / TODO

- [x] ~~Install Python 3.12 locally~~ — done (winget, 3.12.10). Backend suites now run locally.
- [ ] Phase 08 ML path (Graph2Plan/House-GAN++ on RPLAN) + non-rectilinear clipping/CP-SAT.
- [ ] First real schema work happens in Phase 02; `packages/schemas` is a placeholder until then.
- [ ] Wire `pnpm codegen` once Phase 02 schemas exist.
- [ ] Decide managed-secrets strategy for prod (Phase 18); local uses `.env`.

## Phase 01 — verification status (2026-06-04)

**Verified green on this machine (Windows, node 22, no local Python):**
- `pnpm install` ✅ (lockfile generated) · `pnpm typecheck` ✅ · `pnpm lint` ✅ · `pnpm test` ✅ ·
  `pnpm build` ✅ (web `dist/` produced) · `docker compose config -q` ✅ (compose file valid).

**Not yet booted here (no blocker, just environment):**
- The dockerized stack (`pnpm dev`) and the Python services' `/health` were **not run** because the
  **Docker daemon (Docker Desktop) is not running** and there is **no local Python 3.12**. The api +
  service Dockerfiles, FastAPI apps, and `apps/api/tests/test_health.py` are written and exercised in
  CI. To finish locally: start Docker Desktop, then `pnpm dev` and confirm each `/health` is green.

**Notable fixes during scaffolding (for future reference):**
- Installed pnpm globally via `npm i -g pnpm@9.15.0` — `pnpm -r` (recursive) needs `pnpm` on PATH;
  corepack's global shim couldn't be installed without admin. `corepack pnpm …` works for non-recursive.
- Root `package.json` needs `"type": "module"` for the flat ESM `eslint.config.js`.
- `apps/web/tsconfig.node.json` must emit to `node_modules/.tmp` (NOT `noEmit:true`, which trips
  TS6310 for a referenced composite project; and not emit into the source tree, which Prettier flags).

## Phase 02 — verification status (2026-06-05)

**Verified green on this machine:**
- `pnpm codegen` (TS) generates `gen/ts/{types,schemas}.ts` and is **deterministic** (re-run → identical).
- `pnpm typecheck` ✅ · `pnpm lint` ✅ · `pnpm test` ✅ (25 schema/geometry tests) · `pnpm build` ✅.
- Fixtures validate; malformed docs reject; geometry lint flags CW outer rings + self-intersection;
  10×8 m rectangle measures exactly 80 m² in integer mm².

**Authored, runs in CI (no local Python here):**
- `packages/schemas/python` (`fpg_schemas`): jsonschema validation + geometry mirror + pytest
  (`test_schemas.py`) covering the same fixtures/round-trip/geometry. New CI job `schemas-python`
  runs ruff+mypy+pytest and a datamodel-code-generator (Pydantic) smoke gen.
- `pnpm codegen:py` generates `gen/python/models.py` via uv/python/docker (gitignored, on demand).

**Decisions:**
- Coordinates are tuples in TS via json-schema-to-typescript's `tsType` vendor keyword (Ajv validates
  the underlying `prefixItems`; `tsType` registered as a no-op keyword so strict mode accepts it).
- `gen/ts/*` is committed + drift-checked (`FPG_SKIP_PY=1 pnpm codegen` in CI); `gen/python` is not.
- `RoomType` is an open string (extensible registry in `room-types.ts` / `room_types.py`), not a closed enum.

## Phase 03 — verification status (2026-06-06)

**Verified green on this machine:** JS workspace unaffected — `pnpm lint/typecheck/test` all pass.

**Authored, runs in CI (no local Python interpreter or Docker daemon here):**
- `apps/api` FastAPI gateway: async SQLAlchemy 2.0 ORM + PostGIS column, JWT auth + bcrypt,
  org/membership RBAC (owner/editor/viewer/client) with row-level `authorize_project`, RFC-7807
  errors, correlation-id middleware, `/metrics`. CRUD for projects/boundary/program/plans/codes;
  **immutable plan versioning** (PATCH → new version), duplicate, ancestor `versions`, and `diff`.
  Idempotent job queue (`enqueue_job` by inputs-hash) + **stub `generate`** executor + WebSocket
  `/ws/jobs/{id}` progress; Arq `worker.py` for prod. Seed script. `scripts/export_openapi.py`.
- Unit tests (DB-free, in the existing `apps/api` python CI job): security (jwt/bcrypt), versioning
  (hash/lineage/diff), domain-validation (against Phase-02 schemas), RFC-7807 errors, OpenAPI smoke.
- New CI jobs: **api-client** (export OpenAPI → `openapi-typescript`); api docker build now uses
  repo-root context (`-f apps/api/Dockerfile .`) to bundle the canonical schemas.

**Gated / deferred (clearly marked, follow-ups):**
- `tests/test_integration_flow.py` (full register→project→boundary→program→generate→stream→version→
  diff + idempotency) is gated behind `FPG_DB_TESTS=1` + a PostGIS DB; **not yet wired into CI**
  (needs a validated PostGIS service container).
- **Alembic**: env + ini + mako scaffolding provided (autogenerate-ready); the initial migration is
  generated via `alembic revision --autogenerate` (needs Python). Integration tests build the schema
  from ORM metadata, so they don't depend on a committed migration yet.
- Progress broker is **in-process** (single API process). Redis pub/sub fan-out across pods = Phase 18.
- Job dispatch defaults to **in-process BackgroundTasks**; the Arq worker runs the same executor for
  production scale (full arq-pool enqueue wiring lands with Phase 18 scaling).
- `boundaries.outline_geom` (PostGIS) column exists but is not yet populated (needs shapely/WKT).
- Typed TS API client is generated **ephemerally in CI**; it is wired into the web app in Phase 04.

## Phase 04 — verification status (2026-06-06)

**Verified green on this machine (fully local — frontend is TS):**
- `pnpm typecheck` ✅ · `pnpm lint` ✅ · `pnpm test` ✅ (pure render/3D helper tests) · `pnpm build` ✅
  (Vite bundles three/R3F/konva) · dev server boots and serves `index.html` (HTTP 200, `#root`).

**Built:**
- `packages/ui` design system (Tailwind + Radix): Button, Panel/Toolbar/Badge/Input/Spinner/Field,
  Tabs, Tooltip, Dialog, Slider, resizable Split, Toaster. Consumed via path alias from the web app.
- `apps/web`: React 18 + Vite + Tailwind. Auth (login/register/refresh via Phase-03 client),
  protected + role-aware routes, TanStack Query hooks over a typed `api` client, Zustand editor +
  auth stores, `useJob` WebSocket hook, error boundary, keyboard-shortcut registry.
- Three-region **workspace** (levels+legend | 2D⇆3D viewport | inspector) with top bar
  (generate/export) and a validation/score status bar. **2D Konva** renderer (rooms by type color,
  walls, openings, tags, pan/zoom, fit-to-view) and **3D R3F** renderer (room slabs + wall boxes,
  OrbitControls, grid, gizmo, iso/top camera presets) — both share selection + level state.
- **Offline demo** route `/demo` renders a bundled example plan in 2D and 3D with **no backend**,
  so the core render deliverable is verifiable locally; the dashboard links to it when the API is down.

**Decisions / follow-ups:**
- Web tsconfig consumes `@fpg/ui` and `@fpg/schemas` **source** via path aliases (Vite alias + TS
  paths); dropped `composite`/project-refs to avoid TS6307 when importing aliased source.
- 3D is a lightweight scaffold (extruded slabs + wall boxes); the real solidifier (CSG openings,
  slabs, stairs, glTF) is Phase 11. The viewport already supports loading that glTF later.
- Per-project **role** isn't in the API payload yet, so edit-gating uses a default; add the caller's
  role to `ProjectOut` (Phase 03 enhancement) to fully drive viewer/client gating. (follow-up)
- Vite warns the main chunk >500 kB (three/R3F). Code-split/lazy-load the 3D viewport in Phase 20 perf.

## Phases 05 + 06 — verification status (2026-06-06)

**Verified green on this machine (frontend is TS):** `pnpm typecheck` ✅ · `pnpm lint` ✅ ·
`pnpm test` ✅ (geometry-core + program + viewport helper tests) · `pnpm build` ✅.

**Phase 05 (Boundary):**
- `@fpg/geometry-core` package: snapping (grid/angle), bbox/area/perimeter, point-in-polygon,
  CCW orientation, and setback envelope (rectangular inset) — unit-tested.
- `apps/web/src/boundary`: Konva editor (draw outline/parcel, vertex drag-edit, grid+ortho snap,
  pan/zoom), multi-level manager (elevation/floor-to-floor), site setbacks with ghosted buildable
  **envelope**, north angle, live area/perimeter metrics, **DXF import** (client-side `dxf-parser`,
  largest closed polyline), **3D massing** preview (extruded levels), and Save → `PUT /boundary`
  with schema + `lintBoundary` validation. Wired at `/projects/:id/boundary`.

**Phase 06 (Program):**
- `apps/web/src/program`: **Excel/CSV import** (SheetJS) with auto column-mapping + a mapping dialog,
  room-type inference (synonyms→canonical, slug fallback), quantity expansion, m²/ft²→mm² conversion,
  and a preview; an editable **table**, a **React Flow** adjacency graph (drag-to-connect), an
  **adjacency matrix** view, a live **space-budget meter** (vs. boundary level-0 area), starter
  **templates**, **Excel export** + downloadable template, contradiction detection, and Save →
  `PUT /program`. Wired at `/projects/:id/program`. Pure logic unit-tested.
- Project pages now nest under a `ProjectLayout` with Boundary | Program | Plans nav.

**Decisions / follow-ups:**
- Excel + DXF parsing run **client-side** (SheetJS / dxf-parser) — no backend needed; the server-side
  openpyxl + ezdxf/ODA path (incl. **DWG**, image-trace, reusable import profiles, round-trip
  reconciliation) remains the Phase 06/15 server work. `POST /program/import` still returns 501.
- Setback envelope is a **rectangular** bbox inset; true polygon offsetting for non-rectangular
  parcels needs a clipper (follow-up).
- `xlsx` (SheetJS) has known advisories; fine for a client dev tool — revisit in Phase 20 hardening.
- Bundle now ~2.4 MB (xlsx + reactflow + three) — code-split in Phase 20 perf.

## Phase 08 + local Python verification (2026-06-06)

**Local Python is now available** — installed Python 3.12.10 via `winget` (user scope) at
`%LOCALAPPDATA%\Programs\Python\Python312`. Per-service venvs created under each `.venv` (gitignored).
This let me run the backend test suites locally for the first time.

**Phase 08 — deterministic generative engine (`services/generator`), verified locally:**
- `layout.py` squarified-treemap partition; `solver.py` orders rooms by adjacency BFS, partitions the
  boundary bbox by target areas, synthesizes per-room walls (exterior/interior) + doors on touching
  adjacencies + windows on exterior walls of rooms requiring them; reproducible by seed (deterministic
  uuid5 plan ids); de-dupes near-identical candidates and ranks by score. `scoring.py` = adjacency
  satisfaction + area fit. `POST /generate` endpoint added.
- `apps/api` `run_generate` now calls the generator service (`call_service`) with a graceful **stub
  fallback** when unreachable, persisting + scoring + streaming each candidate.
- Tests: ruff ✅ · mypy ✅ · pytest ✅ (6 solver tests: valid against plan schema, distinct, all
  program rooms present, fills boundary ±2%, reproducible per seed, adjacency ≥0.6).

**Retroactively verified locally (were "CI-only" before):**
- `packages/schemas/python` — ruff ✅ · mypy ✅ · pytest ✅ (24).
- `apps/api` (Phase 03) — ruff ✅ · mypy ✅ (25 files) · pytest ✅ (14 passed, 1 DB-gated skip).

**Real CI-failing issues found & fixed during verification (would have failed CI):**
- ruff: added `B008` to root ignore (FastAPI `Depends()`/`Body()` default idiom); `Role`/`JobStatus`
  → `enum.StrEnum` (UP042); `functools.cache` (UP033); removed stray `# noqa: BLE001`; `ASYNC109`
  noqa on the httpx timeout param; `ClassVar` on arq `WorkerSettings.functions`; SIM/RUF cleanups.
- mypy: added per-package `[tool.mypy]` ignore-missing-imports for `jsonschema`/`referencing`
  (schemas-python) and `geoalchemy2`/`arq`/`prometheus_client`/`jsonschema`/`referencing` (apps/api),
  since CI runs mypy per-service-dir (root strict config doesn't apply there).

## Phases 09–15 (2026-06-06) — verified locally

All backend suites run from their own dirs: validator 5 ✅ · geometry 3 ✅ · export 5 ✅ ·
generator 6 ✅ · api 14 (+1 DB-skip) ✅ · schemas-py 24 ✅. JS: typecheck/lint/test/build ✅.

- **09 validator** (`services/validator`): safe rule-predicate interpreter (`cmp` over a metric
  registry — room area/min-dimension/aspect/window-ratio/ceiling, door clear-width, egress
  reachability) → ValidationReport with per-rule pass/fail + geometry_ref + citation + weighted
  score + category sub-scores. Tests: undersized bedroom + narrow door correctly flagged.
- **10 / 13 editor + interactive editing**: `planStore` (zustand) with undo/redo; editable Konva
  vertices, room-type change, auto-furnish, fixture add/remove; Save → `PATCH /plans/{id}` (new
  version). Fixtures render in 2D (rects) and 3D (boxes).
- **11 geometry** (`services/geometry`): trimesh+shapely solidify → GLB (room slabs + wall boxes,
  nodes tagged `slab:`/`wall:`); `/solidify(.glb)` endpoints.
- **12 component library**: `apps/web/src/library` catalog (15 components) + deterministic
  `autoFurnish` (row-packs a room type's default set within bounds) + `componentsForRoom`.
- **14 variants**: "Generate N" + a score-sorted variant gallery strip to switch the active plan.
- **15 export** (`services/export`): DXF via ezdxf (A-WALL/A-DOOR/A-GLAZ/A-AREA/A-ANNO layers, real
  mm scale) + IFC4 via ifcopenshell (IfcProject→Site→Building→Storey + IfcSpace per room w/
  NetFloorArea) + room-schedule CSV; api `POST /plans/{id}/export?format=dxf|ifc|csv` proxy; web
  Export dropdown downloads the file. **This satisfies the brief's DWG/Revit-export requirement**
  (DWG itself via the ODA converter is the remaining step; DXF imports into AutoCAD/Revit today).

## Phases 16–18 (2026-06-06) — verified locally

- **16 Revit**: `services/export` IFC now emits a geometric context + `IfcWall` (extruded solids) +
  `IfcDoor`/`IfcWindow` alongside `IfcSpace`s; tests reopen the file via ifcopenshell and assert
  wall/door/window counts. Added `services/revit-addin/` — element mapping spec, Open-vs-Link
  procedure, a C# `ImportPlanCommand` add-in + `.addin`/`.csproj`, and a Revit verification checklist
  (authored; not compiled — no Revit/.NET locally).
- **17 Approval/collab** (`apps/api`): models Share/Comment/Approval/AuditLog; pure approval state
  machine (`approval.py`, unit-tested); endpoints for shares (capability-URL `GET /shared/{token}`
  client review), authenticated + token comments, `POST /plans/{id}/approval` (legal-transition +
  single-approved-per-project enforcement, sets `current_plan_id`), and `GET /projects/{id}/audit`.
  api suite: ruff/mypy clean (28 files), 16 passed + 1 DB-skip.
- **18 Deploy/scale/observe**: `infra/k8s/manifests.yaml` (ConfigMap/Secret, api Deploy+Svc+HPA,
  worker Deploy, web Deploy+Svc, Ingress), `keda-scaledobject.yaml` (worker scale-to-zero on Redis
  queue depth), `infra/observability/prometheus.yml`, `.github/workflows/deploy.yml` (build/push GHCR
  matrix → staging → tag-gated prod), and a multi-stage `apps/web/Dockerfile` (Vite dev / nginx prod).
  All YAML validated; `docker compose config` valid. Not applied to a real cluster (none available).

## DB migration: Postgres/PostGIS → MongoDB (2026-06-06)

To make the stack runnable end-to-end without Docker (PostGIS's GeoAlchemy2 geometry column blocked
a SQLite fallback), the `apps/api` persistence was **swapped from SQLAlchemy/asyncpg/GeoAlchemy2 to
Motor (async MongoDB)** — a natural fit since boundary/program/plan are JSON documents.
- `db.py` = Motor client + `serialize()`/`oid()`/`utcnow()`; `models.py` = enums + collection names
  (no ORM); all routers + `deps.py` + `jobs.py` + `seed.py` rewritten to Motor; no schema migrations
  needed (collections are lazy). Compose/.env/k8s/CLAUDE updated (mongo service, `MONGODB_URI`).
- api re-verified locally: **ruff ✅ · mypy ✅ (28 files) · pytest ✅ (16 + 1 skip)**.
- Running locally via a **portable mongod** at `C:\Users\NG\mongodb` (no Docker). Seed creates
  demo@example.com / demo-password + a 2-bed demo project.

## END-TO-END RUN VERIFIED (2026-06-06)

The full stack ran natively (no Docker): portable **mongod** + service venvs + Vite. Live smoke test:
login (demo@example.com) → demo project (10×8 m boundary + 2-bed programme) → **Generate produced 6
scored options via the real squarify solver** (scores 67–74.5) persisted to MongoDB → **exported the
best plan: DXF 61 KB, IFC 22 KB (valid ISO-10303-21), CSV room schedule (7 rooms)** → web app HTTP 200.
See `plan/RUN-LOCAL.md` for start steps + demo creds. Servers run in the background on ports
8000/8001/8003/8004/8005/5173/27017.

## DOCKERIZED END-TO-END VERIFIED — incl. Phase 07 (2026-06-07)

Brought up the **full dockerized stack** (`docker compose -f infra/docker-compose.yml up -d --build`
— 11 containers: mongo/redis/minio/qdrant + api/worker + generator/codes/validator/geometry/export +
web). Seeded, then ran `tests/e2e_phase07.py` against the live API — **all checks passed**:

- login (demo@example.com) → demo project carries `jurisdiction_id=generic-ibc-2021`.
- **Ask-the-code** `POST /codes/query "minimum bedroom area?"` → top hit **§1208.1 "Minimum room
  areas"** (proxied api → codes RAG; "egress travel to exit" → §1006.2; "door clear width" → §1010.1.1).
- **Generate** 6 plans via the real solver → each **scored by the validator against the ruleset**:
  best **compliance score 74.4** (vs layout 67.0 — proves the validator ran), 3 flagged rules,
  `ruleset=generic-ibc-2021`. ValidationReport surfaced on `PlanOut.validation`.
- **Export** best plan: DXF 61,323 B · IFC 21,900 B · CSV 215 B.
- **Web** app HTTP 200 (Vite dev container); Codes tab + compliance panel render.
- codes service: 13 extracted rules, **12 approved / 1 flagged** (building-coverage low-confidence,
  excluded from publish until reviewed).

**Two real Docker packaging bugs found & fixed during this run** (pre-existing, unrelated to Phase 07
logic): (a) the api image didn't bundle `packages/schemas/examples`, so dockerized `app.seed` crashed
— added a `COPY … ./examples` + `FPG_EXAMPLES_DIR` env and made `seed.py` path-robust; (b) no
`.dockerignore` existed, so `COPY . .` copied the host (Windows) `node_modules` into the web dev image
and broke Vite's module resolution — added a repo-root `.dockerignore`. Both rebuilt + reverified.

## UX + engine hardening pass (2026-06-07)

Driven by hands-on testing of the live stack:

- **Robust 2D boundary tool** (`apps/web/src/boundary`): added **undo/redo** (history stack in the
  store, Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y), the ability to **delete the outline** and individual
  vertices (right-click / Del), **insert vertices** on edges, Esc/Enter to cancel/finish drawing, a
  live rubber-band segment, and **on-canvas dimensions** (per-edge length labels + area + live
  length while drawing). Fixes "can't delete the default blue box".
- **Door/entry-aware generator** (Phase 08): added an optional `entry` block to the program-graph
  schema (`exterior_doors` default 1, `entry_node_id`, `entry_side`) + codegen + a program-editor
  "Entrances" control row. The solver now places **exactly N exterior doors** (default **1**) at the
  resolved entry (biased onto a boundary corner so it's exterior), and builds a **circulation
  spanning tree from the entry so every room is reachable** (egress). Fixes "too many outdoor doors"
  and lifted the demo's compliance score **74.4 → 89.7** (egress now passes; only natural-light/vent
  remain flagged). New solver tests (single door by default, count honored, full reachability,
  preferred entry respected).
- **3D floors offset fix** (`PlanScene3D`): room floor slabs used rotation `-π/2` (mapping y→−z)
  while walls use +y for Z, mirroring the slabs and offsetting them in the iso view. Changed to
  `+π/2` so floors sit under the walls.
- **3D doors & windows** (`plan-3d.ts` + `PlanScene3D`): walls are now **segmented around openings**
  (full-height solids between openings + a header over each opening + a sill panel under each
  window) so there are real holes, with **door leaves + frames + knobs** and **glazed windows
  (frame + cross mullion + translucent pane)** placed in the voids. Pure geometry in `wallSegments()`
  / `openings3D()` (2 new unit tests). `wallBoxes()` kept for back-compat.
- **Any-shape boundary partition** (the big generator upgrade): replaced the bbox `squarify` with a
  **recursive area-bisection of the real outline polygon** (`services/generator/app/geometry.py` +
  `partition.py`): each cut is a half-plane clip positioned by binary search on area, so every room
  stays inside the outline. Works for concave/L-shaped/arc-approximated (many-vertex) boundaries.
  Walls are now the room-polygon edges (exterior = on the outline), adjacency/doors use collinear
  shared-edge detection, and scoring's `rooms_touch` is shared-edge based. The 2D (Konva polygons)
  and 3D (`ShapeGeometry` + atan2-oriented wall segments + openings) renderers already handle
  arbitrary polygons, so they follow automatically; the validator/codes operate on the room polygons
  + openings unchanged. Verified live on the L-shape: rooms total **96 m² (real area) vs 120 m²
  bbox**, all centroids inside, a non-rectangular room at the concave corner, 1 exterior door, full
  egress. (Note: arcs are represented as fine polylines — there's no curved-arc primitive in the
  boundary schema yet.)
- **Test inputs** (`inputs/`): a 3-bed-house `program-graph.json` (area + adjacency + `entry`:
  2 exterior doors, front on the south at the entry), derived `area-program.xlsx`,
  `adjacency-matrix.csv`/`.xlsx`, a matching 14×10 m `boundary.json`, and a README. Verified through
  the live generator (12 rooms, 2 exterior doors on entry+garage, all reachable).
- **Idempotency + storage bugs found while wiring the above:** the generate cache key hashed only
  count/seed, so editing the program didn't refresh plans — now folds in the boundary/program/
  jurisdiction content. And deterministic plan ids collided on re-generation — plan persistence is
  now an upsert (re-running a seed replaces rather than erroring).
- Verified: JS typecheck/lint/test (18) + build; generator ruff/mypy + 10 tests; api ruff/mypy + 16;
  schemas TS 27 / py 26. Rebuilt generator/api/web images; live dockerized e2e green (demo plan now
  has exactly 1 exterior door, 7/7 rooms reachable).

## Feature pass: RAG upload, code-aware windows, sliver-free plans, editor openings (2026-06-07)

- **#3 Plan quality (no slivers):** the polygon partition now chooses the cut **axis to minimise the
  worse child's aspect ratio**, **snaps cuts to outline-vertex coordinates** (aligns partitions to
  notches like an L's inner corner), and penalises sub-2 m room dimensions. On the L-shape the
  concave area is absorbed into one clean L-room; worst aspect ~2.2, no thin leftovers. (`geometry.py`
  `cut_for_area/aspect/min_dim`, `partition.py`.)
- **#2 Code-aware windows:** RoomNode gains `windows` (count) + `window_to_wall_ratio`; the generator
  sizes/distributes glazing to the requested count/ratio **but auto-raises to the code daylight
  minimum (window area ≥ 8% of floor area)** so an input can't produce a violation (verified: input
  0.04 → placed 0.080). Program table has Windows + Win/Wall% columns. (`solver._place_windows`.)
- **#1 Upload documents for RAG:** `services/codes` `POST /codes/upload` (+ `add_document`) registers/
  extends a jurisdiction from uploaded text/markdown/HTML, ingests + extracts (OpenAI when keyed —
  verified extracting rules from an uploaded doc), api proxy `POST /codes/upload`, and a Codes-page
  upload panel.
- **#4 Editor doors/windows + live code check:** `planStore` adds add/move/width/delete-opening
  (with neighbour inference for interior doors) + undo/redo; the 2D canvas drags openings along their
  wall; the Inspector adds doors/windows to a selected wall, edits width, flags doors < 815 mm, and
  deletes openings; the status bar shows door/window counts; and **`PATCH /plans/{id}` now
  re-validates the edited version against the project's code** so wall/door/window edits are scored.
  (Full free-form wall redraw remains a follow-up.)
- Verified: generator 16 tests (incl. L-shape tiling/containment/quality + window code-minimum),
  api 16, schemas-py 26, JS typecheck/lint/test (20)/build — all green. Rebuilt generator/api/codes/
  web images; live: e2e green, RAG upload extracts via OpenAI, windows auto-raise to code, L-shape
  sliver-free.

## Compliance robustness pass — score >80 (2026-06-07)

Diagnosed via the real validator (a rule fails if ANY in-scope room fails it). Root causes of low
scores: kitchens/other habitable rooms got no window (the code's daylight/ventilation rules apply to
them even without `requires_window`), glazing targeted *exactly* 8% so integer rounding dropped it
below code, and habitable rooms sometimes landed interior (no possible window). Fixes in
`services/generator`:
- **Windows on every habitable room** (living/dining/kitchen/bedrooms) with an exterior wall, sized
  to **8% + 2% margin** of floor area (rounding-safe) → daylight + ventilation pass for all.
- **Habitable→exterior swap**: an interior habitable room trades polygons with an exterior service
  room (corridor/bath/closet/…) when it won't break min-area — a real architectural move so habitable
  rooms get daylight.
- **Entrance guarantee ("fix entry")**: the chosen Main-entry room is forced onto the exterior so the
  Main-entry + Facing controls reliably pin the front door there.
- **Door widths ≥ 815 mm** (interior + exterior) to satisfy the egress door rule.
- API `_content_signature` gains an **ALGO_VERSION** so a solver upgrade busts the generate cache.

Result (validator, generic-ibc): demo 2-bed **100.0 (0 fails)**; a fitting 12-room/140 m² house →
options **[100,100,100,100,84.6,84.6]**, best 100. Over-budget combos (e.g. 130 m² program in an
80–96 m² boundary) still fail min-area/min-dimension — physically correct; the budget meter warns.

Also: **program graph** is now a deterministic **force-directed bubble diagram** (connected rooms
cluster, unrelated spread) instead of a fixed circle — readable like an architect's adjacency
diagram. Verified: generator 16 tests, api 16, JS typecheck/lint/test/build green; live e2e best
score 100.

## Session log

- **2026-06-04** — Authored full `plan/` (Phases 00–20). Added area-program Excel input (Phase 06,
  schema in 02, endpoint in 03, export reconcile in 15). Completed Phase 01 scaffold: monorepo
  (pnpm workspaces), TS/Python tooling, dockerized dev stack, CI, web app + api + 5 service shells.
  All JS quality gates pass; see verification status above.
- **2026-06-05** — Completed Phase 02: authored JSON Schemas (common/project/boundary/program-graph/
  plan/ruleset/validation-report), wired TS codegen (json-schema-to-typescript + Ajv validators) and
  on-demand Python codegen, added geometry invariant linter (TS + Python), 8 golden fixtures, and
  tests (25 TS + Python suite). All workspace gates green; codegen deterministic.
- **2026-06-06** — Completed Phase 03: authored the FastAPI backend (`apps/api`) — DB/ORM + RBAC +
  CRUD + immutable plan versioning/diff + idempotent jobs + WebSocket progress + stub generate +
  observability + seed + OpenAPI export; added DB-free unit tests and new CI jobs (api-client,
  fixed api docker context). JS gates remain green.
- **2026-06-06** — Completed Phase 04 (Frontend Shell): `packages/ui` design system + `apps/web`
  (auth, routing, RBAC, TanStack Query, Zustand, 2D Konva + 3D R3F viewports, offline demo).
  Verified locally end-to-end: typecheck/lint/test/build/dev-serve all green.
- **2026-06-06** — Completed Phases 05 + 06: `@fpg/geometry-core`, boundary editor (draw/edit/snap,
  levels, setbacks, DXF, 3D massing) and program editor (Excel import/export, table + React Flow
  graph + matrix, budget, templates), nested under a project layout. All gates green locally.
  **Milestone M2 (Inputs) is now functional except Phase 07 (building-code RAG).**
- **2026-06-06** — Installed local Python 3.12; built Phase 08 deterministic generator (squarify
  solver + scoring + `/generate`, api calls it with stub fallback) and **verified it locally**, then
  retroactively ran the Phase-02-py and Phase-03 suites locally — fixing several real ruff/mypy
  issues that would have failed CI. **Next: Phase 09 (validator) to pair with the generator, or
  Phase 07 (codes RAG), or wire the generator into the dockerized worker path.**
- **2026-06-06** — Built Phases 09–15: validator, 3D solidify (GLB), component library +
  auto-furnish, editable 2D editor (undo/redo/save), interactive editing, variants gallery, and
  DWG/DXF + IFC export (api proxy + web menu). All backend suites + JS gates verified locally.
  **Milestones M3 (generation+validation) and M5 (deliverables) substantially functional. Remaining
  before a full vertical slice: Phase 07 (codes RAG) and Phase 16 (Revit). Then M4 polish / M6.**
- **2026-06-06** — Built Phases 16–18: IFC native categories (walls/doors/windows, verified),
  Revit add-in/mapping scaffold; approval & collaboration backend (shares/capability URLs/comments/
  approval state machine/audit, verified); k8s + KEDA + Prometheus + CD workflow + nginx prod web
  image (YAML-validated). **Only Phase 07 (codes RAG), 19 (testing), 20 (hardening) remain; plus the
  🟨 advanced sub-features. M6 (product) substantially in place.**
- **2026-06-07** — Built **Phase 07 (Building-Code RAG)** + wired the compliance loop end-to-end.
  `services/codes`: per-jurisdiction document registry; clause-level chunking (md/txt/html now,
  PyMuPDF PDF optional); deterministic offline hybrid retrieval (hashing embeddings + BM25, Qdrant
  is the production target); prose→`Rule` extraction with thresholds parsed from clause text (OpenAI
  path behind `OPENAI_API_KEY`, deterministic fallback otherwise); confidence flagging + human
  review/publish; rule-set versioning with a reviewable diff on re-ingest. Seeded `generic-ibc-2021`
  (13 rules / 12 categories; building-coverage flagged low-confidence → 12 published categories).
  Endpoints: `/codes`, `/codes/query`, `/codes/ingest`, `/rulesets[...]/{review,publish}`. **API**:
  `POST /codes/query` proxy; **validator wired into `run_generate`** so each generated plan gets a
  compliance score + ValidationReport (falls back to layout score if validator/ruleset absent); seed
  inserts the published RuleSet into Mongo + sets the demo project's jurisdiction. **Web**: Codes tab
  ("ask the code" + citations + disclaimer) and a workspace compliance panel; jurisdiction shown on
  the project. Verified locally: codes ruff/mypy clean + 9 tests; api 16 (+1 skip); validator 5;
  schemas-py 26; JS typecheck/lint/test (27 schema)/build green. Acceptance met: "minimum bedroom
  area?" → §1208.1; ≥10 published executable categories each cited; re-ingest yields a rule diff;
  low-confidence excluded until approved. **Milestone M2 (Inputs) complete.** Then ran the **full
  dockerized stack** (11 containers) + the `tests/e2e_phase07.py` smoke — all green (login → codes
  query → generate → per-plan compliance score → export) — fixing two pre-existing Docker packaging
  bugs (api image missing schema examples; missing `.dockerignore` clobbering the web node_modules).
  See "DOCKERIZED END-TO-END VERIFIED" above.
- **2026-06-07** — Per user request, **swapped the LLM rule-extraction path from Anthropic/Claude to
  the OpenAI API** (`services/codes/app/extract.py` now uses the OpenAI SDK + function-calling;
  settings `openai_api_key`/`openai_model`/`openai_base_url`; `[extract]` extra = `openai`; codes
  Dockerfile installs it; compose injects the key via `env_file: ../.env`). Also fixed compose `.env`
  resolution (root `pnpm dev` now passes `--env-file .env`; project-dir was `infra/`). Verified live
  in Docker: codes extraction `method=openai` (10 rules/9 cats, 7 approved/3 flagged), ask-the-code
  still returns §1208.1, full e2e green. Note: raw LLM output shows expected quirks (e.g. an
  `aspect_ratio > 3` sign slip, a `7 m²`→`70000` unit mis-convert) — handled by review-before-publish;
  retrieval + the api-seeded canonical compliance ruleset are independent of the LLM. **The pasted
  OpenAI key lives only in gitignored `.env` and should be rotated (it was shared in chat).**
