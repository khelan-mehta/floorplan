# @fpg/schemas — the canonical domain model (source of truth)

Every service consumes types from here. **Do not** hand-roll payload shapes elsewhere.

## Layout

```
schemas/        JSON Schema (draft 2020-12) — THE source of truth (hand-authored)
examples/       golden fixtures that must always validate
src/            stable TS wrappers: validate (Ajv), geometry invariants, room-types
gen/ts/         GENERATED TypeScript: types.ts (interfaces) + schemas.ts (runtime consts)
gen/python/     GENERATED Pydantic models (on demand; gitignored)
python/         fpg_schemas — Python validation + geometry mirror (+ tests)
scripts/        codegen orchestrators
```

## Codegen

```bash
pnpm codegen           # from repo root: regenerate gen/ts/* (TS types + schema consts)
pnpm codegen:py        # also generate gen/python/models.py (needs uv / python / docker)
FPG_SKIP_PY=1 pnpm codegen   # TS only (what CI's drift check runs)
```

`gen/ts/*` is **committed** and drift-checked in CI (regenerate → `git diff --exit-code`).
`gen/python/models.py` is generated on demand and **not committed** (datamodel-code-generator).

## Conventions

- **Units & coordinates:** all geometry is **integer millimetres**. `Vec2 = [x, y]`,
  `Vec3 = [x, y, z]`. Frame: +X east, +Y north, +Z up; origin at the boundary bbox-min.
  Display units (`m`/`ft`/…) are presentation-only.
- **Every root document carries `schema_version`** (currently `1`, enforced as a `const`).

## Geometry invariants (enforced by `lintPolygon` / `lint_polygon`)

1. Rings have ≥ 3 points; closure is implicit (do not repeat the first point).
2. Coordinates are integers (mm).
3. **Outer ring is CCW** (positive signed area); **holes are CW** (negative).
4. Rings are **simple** — no self-intersections.
5. Non-zero area.

Schema validation checks structure/types; geometry validity is a **separate** check because JSON
Schema cannot express it. Always run both on ingest (`assertValid` + `lint*`).

## Schema versioning & migration policy

- Bump a root document's `schema_version` only on a **breaking** change to that document.
- Additive, backward-compatible changes (new optional field) do **not** bump the version.
- On a bump: add a migration in the consuming services and update fixtures + this package's
  `const` (and the codegen). Old documents are migrated forward on read, never mutated in storage
  in place (see the versioning rule in `CLAUDE.md`).

## Rule predicate DSL (consumed by the validator, Phase 09)

`Rule.predicate` is a small, safe AST (`op`: `cmp | all | any | implies | and | or | not`). A `cmp`
node references a **metric** evaluated against a derived geometry model, e.g.:

| metric | meaning |
|--------|---------|
| `room.area_mm2` | finished floor area |
| `room.min_inscribed_width_mm` | narrowest usable width |
| `door.clear_width_mm` | clear opening width |
| `corridor.min_width_mm` | narrowest corridor width |
| `egress.travel_distance_mm` | distance to nearest exit |
| `window.area_ratio` | window area ÷ room floor area |
| `stair.rise_mm` / `stair.run_mm` | stair geometry |
| `building.coverage_ratio` / `building.far` | site metrics |

The full metric registry and interpreter live in Phase 09 (`services/validator`). The schema keeps
`predicate` permissive (`additionalProperties: true`) so the registry can grow without schema bumps.
