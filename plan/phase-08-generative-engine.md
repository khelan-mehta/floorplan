# Phase 08 — Generative Layout Engine

**Goal:** The heart of the product. Given a `Boundary`, a `ProgramGraph`, and a `RuleSet`, produce
**K diverse candidate `Plan`s** — rooms placed and sized inside the outline, satisfying adjacencies
and code-derived sizing as best as possible. Two cooperating strategies: a learned generator (ML)
for creativity and a deterministic solver for feasibility/repair.

**Depends on:** Phases 02, 05, 06, 07. Output consumed by Phases 09–14.

> Build the **solver path first** (deterministic, testable, ships the vertical slice), then add the
> **ML path** for creativity. The solver also *repairs* ML output into valid geometry.

---

## Strategy A — Deterministic solver (build first)

1. **Floor partitioning approaches** (implement at least the first two):
   - **Treemap / slice-and-dice / KD-partition:** recursively split the boundary's bounding region
     into rectangles sized by `area_target`, ordered to respect adjacency. Fast, rectilinear,
     reliable for orthogonal boundaries.
   - **Constraint programming (OR-Tools CP-SAT):** variables = room rectangles (x,y,w,h on a grid);
     constraints = inside boundary, non-overlap, area bounds, aspect bounds, adjacency (shared
     edge length ≥ threshold), fixed cores. Objective = weighted adjacency satisfaction + area
     fit + compactness. Excellent for hard constraints; slower.
   - **Voronoi / growth-based** (optional) for organic, non-rectilinear partitions.
2. **Circulation generation:** after rooms, carve corridors/hallways to connect the access graph
   (entry → public → private), ensure every room is reachable, and meet min corridor width.
3. **Wall & opening synthesis:** convert room polygons to a shared wall network (merge coincident
   edges → centerlines → thickness), place doors on adjacency edges, windows on exterior walls of
   rooms that `requires_window`.
4. **Repair operators:** snap-to-grid, merge slivers, enforce min dimensions, straighten walls.

## Strategy B — Learned generator (creativity)

1. **Model lineage** (pick/iterate — start with the simplest that runs):
   - **Graph2Plan** — layout graph + boundary → floorplan (closest to our exact inputs).
   - **House-GAN++** — graph-constrained relational GAN (good baseline, manhattan layouts).
   - **HouseDiffusion / Cons2Plan** — diffusion over room/door coordinates; best diversity and
     handles non-manhattan; heavier to train/serve.
2. **Data:** train/fine-tune on **RPLAN** (and synthetic data from the solver). Map our
   `ProgramGraph` → the model's graph encoding; map our `Boundary` → the model's boundary raster/
   vector input. Document the data license and a `datasets/README` fetch script.
3. **Inference service (`services/generator`, GPU):** input (boundary, graph, ruleset-derived size
   hints, `seed`, `count`) → raw room boxes/polygons → **hand off to Strategy A's repair + wall/
   opening synthesis** so ML output always becomes a valid `Plan`.
4. **Diversity control:** vary seeds, temperature/noise, and adjacency-weight perturbations to get
   genuinely different options (not near-duplicates) for the client-approval workflow (Phase 14).

## Orchestration

- `POST /generate` job (Phase 03) → generator produces N raw layouts → each repaired to a `Plan` →
  each sent to **validator (Phase 09)** → ranked by score → top-K returned with seeds recorded.
- **Idempotent + reproducible:** the same (boundary, program, ruleset, seed) returns the same Plan.
- Stream progress over WebSocket (per-candidate as it completes).

## Tasks

1. Implement the solver path end-to-end (partition → circulation → walls/openings → Plan).
2. Wrap as the `generator` service with the `generate` job contract.
3. Add the ML path behind a feature flag; share the repair/synthesis stage.
4. Diversity sampling + de-duplication (reject layouts too similar by IoU/graph-edit distance).
5. Performance: target a handful of candidates in seconds (solver) / tens of seconds (ML, GPU).

## Deliverables

- Deterministic solver generating valid multi-room `Plan`s for the Phase-02 example boundaries +
  programs.
- ML generator (flagged) producing diverse layouts repaired into valid Plans.
- Ranked top-K results streamed to the client.

## Acceptance criteria

- For a 3-bed program in a rectangular boundary, the solver returns ≥3 distinct valid plans where
  every program room exists, areas are within target tolerance, and adjacency satisfaction ≥ 80%.
- Re-running with the same seed reproduces byte-identical Plans.
- Every room is reachable from the entry (connected circulation), verified by a graph check.
- ML output, after repair, passes `lint_geometry` and produces a valid `Plan` 100% of the time.

## Sources

- Graph2Plan: https://arxiv.org/abs/2004.13204
- House-GAN / House-GAN++: https://arxiv.org/pdf/2003.06988 · https://ennauata.github.io/houseganpp/
- HouseDiffusion: https://arxiv.org/abs/2211.13287 · Cons2Plan: https://openreview.net/pdf?id=Cons2Plan
- RPLAN dataset: http://staff.ustc.edu.cn/~fuxm/projects/DeepLayout/index.html
- OR-Tools CP-SAT: https://developers.google.com/optimization/cp
- rectpack (rectangle packing): https://github.com/secnot/rectpack
- shapely / pyclipper (polygon ops & offsetting): https://shapely.readthedocs.io/ · https://pypi.org/project/pyclipper/

---

## Claude build prompt

> Implement Phase 08 (Generative Layout Engine) per `plan/phase-08-generative-engine.md` in
> `services/generator`. FIRST build the deterministic solver path: partition the Phase-05 boundary
> into room rectangles sized by ProgramGraph area targets using both a slice-and-dice/KD-partition
> method and an OR-Tools CP-SAT formulation (rooms inside boundary, non-overlap, area/aspect bounds,
> adjacency as shared-edge-length constraints, fixed cores; objective = weighted adjacency + area
> fit + compactness); generate circulation/corridors so every room is reachable from the entry with
> min corridor width; synthesize a shared wall network (coincident edges → centerlines → thickness)
> and place doors on adjacency edges and windows on exterior walls of rooms requiring windows; add
> repair operators (snap, sliver-merge, min-dimension enforcement). Wrap this as the `generate` job
> from Phase 03 with reproducible seeds, idempotency, diversity sampling (vary seeds/weights),
> de-duplication by IoU/graph-edit distance, and per-candidate WebSocket progress; rank candidates
> by the Phase-09 validator score and return top-K with seeds recorded. THEN add a feature-flagged
> ML path (Graph2Plan-style to start, with a path to House-GAN++/HouseDiffusion) trained/fine-tuned
> on RPLAN, mapping our ProgramGraph+Boundary to the model's encoding and routing raw model output
> through the SAME repair + wall/opening synthesis so ML results always become valid Plans; document
> dataset fetch/license in `datasets/README`. Acceptance: a 3-bed program in a rectangular boundary
> yields ≥3 distinct valid plans (all program rooms present, areas within tolerance, adjacency
> satisfaction ≥80%, all rooms reachable), identical seeds reproduce identical Plans, and repaired
> ML output passes `lint_geometry` 100% of the time.
