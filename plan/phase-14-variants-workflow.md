# Phase 14 — Variants Generation & Comparison

**Goal:** Generate **multiple distinct plan options**, score and compare them side by side, and
shortlist the best for the client-approval workflow — the "creates several creative options that go
to the client" part of the brief.

**Depends on:** Phases 08, 09, 11, 13. Feeds Phase 17 (approval).

---

## Tasks

1. **Variant generation**
   - "Generate N options" runs the generator with diverse seeds / adjacency-weight perturbations /
     partition strategies, de-duplicates near-identical results (IoU + graph-edit distance), and
     returns a **set** of distinct, valid, scored Plans.
   - Optional axes the user can vary: open-plan vs. cellular, circulation-minimal vs. daylight-max,
     compact vs. spacious — exposed as sliders that bias generation/scoring weights.

2. **Comparison UI**
   - A grid/gallery of variants with thumbnail (2D + 3D snapshot), overall score, and category
     sub-scores (sizing/egress/daylight/circulation/cost). Sort/filter by any metric.
   - **Side-by-side compare** (2–4 variants): synchronized pan/zoom, metric table, diff highlights
     (what differs: room arrangement, areas, adjacency satisfaction).

3. **Scoring & metrics surface**
   - Show validator scores (Phase 09) plus design metrics: total area efficiency (net/gross),
     circulation ratio, daylight reach, adjacency satisfaction %, estimated material/cost proxy.

4. **Shortlisting & annotation**
   - Star/shortlist variants, add notes/tags ("client favorite", "value option"), and assemble a
     curated set to send for approval (Phase 17). Each variant remains fully editable (Phase 13).

5. **Iteration loop**
   - "More like this" — generate variations near a chosen plan (small perturbations) to refine an
     option the team likes.

---

## Deliverables

- N-option generation with diversity guarantees and per-variant scoring.
- A comparison gallery + side-by-side compare with synchronized views and metric diffs.
- Shortlisting/annotation feeding the approval workflow; "more like this" refinement.

## Acceptance criteria

- "Generate 6 options" returns 6 visually distinct, valid plans (pairwise IoU below a threshold),
  each with a score and sub-scores.
- Side-by-side compare synchronizes pan/zoom and highlights the concrete differences between two
  variants.
- Biasing the "daylight" slider measurably increases the daylight sub-score of new variants.
- A shortlisted set can be assembled and handed to Phase 17 with notes intact.

## Sources

- Diversity metrics (IoU, graph-edit distance): https://networkx.org/ (GED) ; shapely (IoU)
- Multi-objective design exploration (concept): https://en.wikipedia.org/wiki/Pareto_efficiency
- (Generation reuses Phase 08; scoring reuses Phase 09.)

---

## Claude build prompt

> Implement Phase 14 (Variants Generation & Comparison) per `plan/phase-14-variants-workflow.md`.
> Add "Generate N options" that runs the Phase-08 generator with diverse seeds, adjacency-weight
> perturbations, and partition strategies, de-duplicates near-identical results via IoU + graph-edit
> distance, and returns a set of distinct, valid, Phase-09-scored Plans; expose design-bias sliders
> (open-plan↔cellular, circulation-minimal↔daylight-max, compact↔spacious) that adjust generation/
> scoring weights. Build a comparison gallery of variants showing 2D+3D thumbnails, overall score,
> and category sub-scores with sort/filter, plus a synchronized side-by-side compare (2–4 variants)
> with a metric table and concrete diff highlights (arrangement, areas, adjacency). Surface design
> metrics (net/gross efficiency, circulation ratio, daylight reach, adjacency satisfaction %, cost
> proxy) alongside validator scores. Add shortlisting/starring with notes/tags that assemble a
> curated set for the Phase-17 approval workflow, keeping every variant editable, and a "more like
> this" refinement that perturbs a chosen plan. Acceptance: "Generate 6 options" returns 6 visually
> distinct valid scored plans (pairwise IoU under threshold), side-by-side compare syncs pan/zoom and
> highlights real differences, the daylight slider measurably raises the daylight sub-score, and a
> shortlist with notes hands off to Phase 17 intact.
