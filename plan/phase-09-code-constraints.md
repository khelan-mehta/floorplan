# Phase 09 — Code Constraints, Validation & Scoring

**Goal:** A pure, deterministic service that takes a `Plan` + `RuleSet` and returns a
`ValidationReport`: per-rule pass/fail with the offending geometry and a verbatim citation, plus a
weighted score. This is the "disposes" half of "the generator proposes; the validator disposes."

**Depends on:** Phases 02, 07, 08. Used by Phases 08 (ranking), 10/13 (live feedback), 14 (compare).

> Keep this service **pure and deterministic** — no network, no randomness. It is the trust anchor
> of the whole product and must be exhaustively unit-tested with golden plans.

---

## The Rule DSL (shared with Phase 07)

A small, safe, serializable predicate language evaluated against a derived **geometry model** of
the plan. No `eval` of arbitrary code — a typed AST interpreted by the validator.

```
Predicate :=
  Comparison(lhs: Metric, op: <=|>=|==|<|>|in, rhs: value|table-lookup)
  | All(scope, Predicate)          # ∀ rooms/doors/... in scope
  | Any(scope, Predicate)
  | Implies(Predicate, Predicate)
  | And/Or/Not(...)

Metric examples (computed by the validator's geometry layer):
  room.area_mm2, room.min_inscribed_width_mm, room.aspect_ratio, room.ceiling_height_mm
  door.clear_width_mm, corridor.min_width_mm
  egress.travel_distance_mm(from=room), egress.exit_count, egress.common_path_mm
  window.area_mm2 / room.floor_area_mm2  (daylight ratio)
  stair.rise_mm, stair.run_mm, stair.headroom_mm, stair.landing
  building.coverage_ratio, building.FAR, setback.distance_mm(side)
```

`rhs` may be a **table lookup** keyed by occupancy/room-type/area (codes are tabular) — resolved
from the `RuleSet` parameters extracted in Phase 07.

---

## Tasks

1. **Geometry analysis layer** (deterministic): from a `Plan`, derive everything the metrics need:
   - room areas, inscribed widths/min-dimensions, aspect ratios, adjacency graph from shared walls,
     door clear widths, corridor widths (medial-axis / max inscribed circle along the path),
     reachability + travel distances (shortest path through circulation to nearest exit),
     exterior-wall detection, window areas per room, stair geometry, building coverage/FAR/setbacks.
2. **DSL interpreter:** evaluate each `Rule.predicate` over the geometry model; produce per-rule
   results with the **specific offending element id(s)** and a human-readable message.
3. **Scoring:** weighted score (errors heavily penalized, warnings lightly); category sub-scores
   (sizing, egress, daylight, accessibility, circulation, site). Return both overall and breakdown.
4. **Explanations & fix hints:** each failure includes the citation (from the rule) and a suggested
   remedy ("widen door to ≥815mm", "bedroom 2 is 6.2m², needs ≥7.0m²").
5. **Service + library:** ship as an importable Python lib (used directly by the generator for
   ranking) AND a thin `validate` job/endpoint (used by editors for live feedback).
6. **Performance:** validate a typical plan in well under a second so the 2D/3D editors can call it
   on every edit (debounced).

---

## Deliverables

- `validator` library + service producing `ValidationReport`s with geometry refs + citations.
- A scoring function with category breakdown used by generation ranking and the UI.
- Golden-file test suite: known plans with known violations → expected reports.

## Acceptance criteria

- A plan with a 6.2 m² bedroom flags the min-area rule, names that room, and cites the clause.
- A door narrower than the rule's width fails the door-width rule with the door id.
- A room with no path to an exit fails egress reachability.
- Validation is deterministic (same input → identical report) and runs < 500 ms on example plans.
- 100% of golden test plans produce the expected pass/fail set.

## Sources

- Shortest-path / reachability: NetworkX https://networkx.org/
- Medial axis / inscribed circle (corridor width): shapely + scikit-geometry / `shapely`
  `maximum_inscribed_circle` (Shapely 2.x): https://shapely.readthedocs.io/
- Egress/travel-distance concepts (IBC ch.10): https://codes.iccsafe.org/
- Polylabel (pole of inaccessibility, for room inscribed width): https://github.com/mapbox/polylabel

---

## Claude build prompt

> Implement Phase 09 (Code Constraints, Validation & Scoring) per `plan/phase-09-code-constraints.md`
> as a pure, deterministic `services/validator` library + thin service. Define the typed, safe Rule
> predicate DSL (Comparison/All/Any/Implies/And/Or/Not over a metric registry, with table-lookup
> rhs for tabular codes) as an interpreted AST — no eval. Build a deterministic geometry-analysis
> layer that derives, from a Phase-02 Plan: room areas, min inscribed widths/aspect ratios, the
> adjacency graph from shared walls, door clear widths, corridor widths via medial-axis/maximum
> inscribed circle, reachability and egress travel distances to nearest exit, exterior-wall and
> per-room window detection, stair geometry, and building coverage/FAR/setbacks. Implement the DSL
> interpreter to evaluate each RuleSet rule and emit per-rule pass/fail with the offending element
> id(s), a human message, the rule's citation, and a fix hint. Add weighted scoring with category
> sub-scores (sizing, egress, daylight, accessibility, circulation, site) returning overall +
> breakdown. Ship both an importable library (used by the Phase-08 generator for ranking) and a
> `validate` job/endpoint (used by editors for debounced live feedback), validating a typical plan
> in <500 ms. Build a golden-file test suite of plans with known violations mapping to expected
> reports. Acceptance: an undersized bedroom flags min-area with the room id+citation, a narrow door
> fails door-width with the door id, an unreachable room fails egress, results are byte-deterministic,
> and 100% of golden plans produce the expected report.
