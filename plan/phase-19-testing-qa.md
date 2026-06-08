# Phase 19 — Testing & QA

**Goal:** A testing strategy that fits this system's unusual mix of deterministic geometry, ML
generation, BIM export, and an interactive 3D UI. Tests are written **alongside** each phase; this
phase defines the strategy, the cross-cutting suites, and the quality gates.

**Depends on:** All phases (it tests them).

---

## Test layers

1. **Unit (per service)**
   - `validator`, `geometry`, `export` are deterministic → exhaustive unit tests with **golden
     files** (input Plan → expected report/GLB/DXF/IFC). Property-based tests (Hypothesis) for
     geometry invariants (areas non-negative, walls connected, openings inside walls).
   - Schema tests: every Phase-02 example validates; malformed docs are rejected.

2. **ML generation tests** (non-deterministic by nature → test properties, not exact output)
   - With a fixed seed, output is reproducible (assert byte-identical).
   - Statistical/contract tests over many seeds: all program rooms present, geometry valid,
     adjacency satisfaction ≥ threshold, no overlaps, all rooms reachable. Track score distributions
     to catch regressions (e.g. mean score drops > X%).

3. **Integration (service-to-service)**
   - api↔worker↔generator↔validator↔geometry↔export happy paths via the job queue; idempotency;
     artifact storage; WebSocket progress.

4. **Geometry/BIM fidelity**
   - Export golden tests: Plan → DXF entities on expected layers; IFC entity counts + spatial tree;
     re-import (ezdxf/ifcopenshell) and compare geometry within tolerance. A **Revit smoke test**
     checklist (manual or scripted via Revit API in CI if feasible).

5. **End-to-end (Playwright)**
   - Full user journeys: draw boundary → build program → generate → edit room → swap component →
     export DWG/IFC → (mock) approval. Visual regression on 2D plan renders and 3D snapshots.

6. **Performance & load**
   - Generation latency benchmarks (solver + ML), validator < 500ms, 3D viewport fps on the example
     building, export job duration. Load tests feeding Phase 18 autoscaling.

7. **Accessibility & cross-browser**
   - axe-core on key screens; keyboard navigation; WebGL support matrix; mobile/tablet viewport.

8. **Quality gates (CI)**
   - Coverage thresholds on pure services (high), schema drift check, golden-file diffs block merge,
     e2e on PR (smoke) + nightly (full), perf budgets fail the build on regression.

---

## Deliverables

- Test suites per layer wired into CI; golden-file corpora for validator/geometry/export.
- Playwright e2e journeys + visual regression baselines.
- ML contract/statistical test harness with score-distribution tracking.
- A Revit fidelity checklist (and scripted check if feasible).

## Acceptance criteria

- CI runs unit+integration+schema+golden+smoke e2e on every PR and blocks on failure/regression.
- Golden-file changes require an explicit, reviewed baseline update (no silent drift).
- The ML harness flags a deliberately degraded model (mean score drop) as a failure.
- A full e2e journey (boundary→generate→edit→export) passes headless in CI.

## Sources

- pytest + Hypothesis: https://docs.pytest.org/ · https://hypothesis.readthedocs.io/
- Playwright: https://playwright.dev/ · Visual regression: https://playwright.dev/docs/test-snapshots
- axe-core: https://github.com/dequelabs/axe-core
- Golden/approval testing: https://approvaltests.com/

---

## Claude build prompt

> Implement Phase 19 (Testing & QA) per `plan/phase-19-testing-qa.md`. Build exhaustive
> deterministic unit tests with golden files for `validator`, `geometry`, and `export` (Plan →
> expected report/GLB/DXF/IFC) plus Hypothesis property tests for geometry invariants and schema
> validation tests for all Phase-02 examples and malformed inputs. Create an ML-generation test
> harness that asserts seed reproducibility and runs statistical/contract checks over many seeds (all
> program rooms present, valid non-overlapping geometry, adjacency satisfaction ≥ threshold, all
> rooms reachable) while tracking score distributions to catch regressions. Add service-to-service
> integration tests across api↔worker↔generator↔validator↔geometry↔export (idempotency, artifacts,
> WebSocket progress), geometry/BIM fidelity tests that re-import exported DXF/IFC and compare within
> tolerance plus a Revit smoke checklist, and Playwright e2e journeys (boundary→program→generate→edit
> →swap→export→mock approval) with 2D/3D visual regression. Add performance benchmarks (generation
> latency, validator <500ms, viewport fps, export duration) and accessibility/cross-browser checks
> (axe-core, keyboard nav, WebGL matrix). Wire CI quality gates: coverage thresholds on pure
> services, schema-drift and golden-file diff gates requiring reviewed baseline updates, smoke e2e on
> PR + full nightly, and perf budgets that fail on regression. Acceptance: CI blocks on any failure/
> regression, golden updates require explicit review, the ML harness flags a deliberately degraded
> model, and the full boundary→export e2e passes headless.
