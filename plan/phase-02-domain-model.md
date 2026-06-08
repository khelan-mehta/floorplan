# Phase 02 — Domain Model & Schemas (the source of truth)

**Goal:** Define the canonical, versioned data model for the entire system as JSON Schema, and
generate typed clients (Pydantic + TypeScript) from it. Every later phase consumes these types.

**Depends on:** Phase 01.

> This is the most important phase. Spend the effort here. A clean model makes generation,
> validation, editing, and export straightforward; a muddy one infects every service.

---

## Core entities (define each as JSON Schema in `packages/schemas`)

### 1. `Project`
```
Project {
  id: uuid
  name: string
  owner_id: uuid
  units: "mm" | "m" | "ft" | "in"            # display only; storage is integer mm
  jurisdiction_id: string | null              # links to a code RuleSet
  boundary_id: uuid | null
  program_id: uuid | null
  created_at, updated_at: datetime
}
```

### 2. `Boundary`  (the outer geometry of the floor + site context)
```
Boundary {
  id: uuid
  north_angle_deg: number                      # for daylight/orientation rules
  levels: Level[]
  site?: { parcel_polygon: Polygon, setbacks: { front,rear,left,right: mm } }
}
Level {
  index: int                                   # 0 = ground
  elevation_mm: int                            # floor-to-floor base
  floor_to_floor_mm: int
  outline: Polygon                             # the buildable outer boundary on this level
  cores?: Polygon[]                            # fixed elements (stair/lift/shafts) to keep
  voids?: Polygon[]                            # courtyards / atria
}
Polygon { rings: Ring[] }                       # ring[0]=outer (CCW), rest=holes (CW)
Ring { points: [int,int][] }                    # mm, closed implicitly
```

### 3. `ProgramGraph`  (the desired rooms + adjacencies — "graph nodes" + area program from the brief)
```
ProgramGraph {
  id: uuid
  source: "graph" | "excel" | "template" | "mixed"   # how it was authored (Phase 06)
  import?: ProgramImport                              # present when authored/updated from a spreadsheet
  nodes: RoomNode[]
  edges: AdjacencyEdge[]
}
RoomNode {
  id: string                                    # stable; quantity-expanded ids like "bedroom-2"
  type: RoomType                               # enum, see below
  label?: string
  department?: string                           # area-program grouping/zone (from Excel)
  level?: int | "any"
  area_min_mm2?: int
  area_target_mm2?: int
  aspect_ratio?: { min:number, max:number }
  count?: int                                   # e.g. 3 bedrooms (expanded on ingest)
  occupancy?: int                               # persons, for code/egress rules
  requires_exterior_wall?: bool                 # window/daylight need
  requires_window?: bool
  fixed_position?: { point:[int,int], lock:bool }
  tags?: string[]                               # "wet", "public", "private", "service"
  source_row?: { sheet:string, row:int }        # provenance back to the uploaded workbook
}
# ProgramImport — captures spreadsheet origin so re-imports reconcile (not clobber) — see Phase 06
ProgramImport {
  artifact_id?: uuid                            # stored uploaded workbook (provenance)
  sheet?: string, header_row?: int
  unit: "m2" | "ft2"                            # source area unit (converted to mm² on ingest)
  column_map: { [roomNodeField: string]: string }   # field → source column header
  profile_id?: string                           # reusable per-firm import profile
  reconcile_key: string[]                       # e.g. ["department","label","index"]
}
AdjacencyEdge {
  a: string, b: string                          # RoomNode ids
  relation: "adjacent" | "connected_door" | "connected_open" | "near" | "not_adjacent"
  weight?: number                               # soft-constraint priority 0..1
}
RoomType enum: bedroom, master_bedroom, bathroom, ensuite, kitchen, living, dining,
  hallway, entry, stair, elevator, closet, laundry, garage, office, balcony, storage,
  mechanical, corridor, lobby, retail, ... (extensible registry, not a closed list)
```

### 4. `Plan`  (a generated/edited floor plan — the system's central artifact)
```
Plan {
  id: uuid
  project_id: uuid
  parent_plan_id?: uuid                         # version lineage
  seed?: int                                    # generator seed for reproducibility
  source: "generated" | "edited" | "imported"
  levels: PlanLevel[]
  score?: number                                # from validator
  created_at: datetime
}
PlanLevel {
  index: int
  rooms: Room[]
  walls: Wall[]
  openings: Opening[]
  fixtures: Fixture[]                           # placed components (Phase 12)
  annotations?: Annotation[]                    # dimensions, room tags
}
Room {
  id: string
  program_node_id?: string                      # back-link to ProgramGraph node
  type: RoomType
  polygon: Polygon                              # finished-floor boundary
  area_mm2: int                                 # derived, stored for fast checks
  centroid: [int,int]
}
Wall {
  id: string
  a: [int,int], b: [int,int]                    # centerline endpoints
  thickness_mm: int
  type: "exterior" | "interior" | "partition" | "shaft"
  height_mm: int
  bears_load?: bool
}
Opening {
  id: string
  wall_id: string
  kind: "door" | "window" | "opening"
  offset_mm: int                                # along wall from endpoint a
  width_mm: int, height_mm: int, sill_mm?: int
  swing?: "left"|"right"|"double"|"slide"
  connects?: [roomId, roomId|"exterior"]
}
Fixture {                                       # furniture / sanitary / appliance
  id: string
  component_id: string                          # → component library (Phase 12)
  room_id: string
  transform: { pos:[int,int,int], rot_z_deg:number, scale?:number }
  params?: object                               # parametric overrides
}
```

### 5. `RuleSet` & `Rule` (machine-checkable building code — produced by Phase 07)
```
RuleSet { id, jurisdiction, version, source_docs[], rules: Rule[] }
Rule {
  id: string
  category: "min_area"|"min_dimension"|"egress"|"door_width"|"ceiling_height"
           |"setback"|"window_area_ratio"|"corridor_width"|"stair"|"accessibility"|...
  applies_to: { room_types?: RoomType[], element?: "door"|"corridor"|"stair"|... }
  predicate: RulePredicate                      # a small DSL, see Phase 09
  severity: "error"|"warning"|"info"
  citation: { doc, section, text }              # traceability back to the code
}
```

### 6. `ValidationReport` (Phase 09 output)
```
ValidationReport {
  plan_id, ruleset_id, score: number,           # 0..100 weighted
  results: { rule_id, status:"pass"|"fail"|"na", message, geometry_ref?, severity }[]
}
```

---

## Tasks

1. Author all schemas in `packages/schemas` as JSON Schema (draft 2020-12), one file per entity,
   with `$ref` reuse for `Polygon`, `Ring`, enums.
2. **Codegen pipeline (`make codegen`):**
   - JSON Schema → Pydantic v2 models (`datamodel-code-generator`).
   - JSON Schema → TypeScript types (`json-schema-to-typescript`) + runtime validators (`ajv`).
   - Output to `packages/schemas/gen/{python,ts}`; both apps import only generated types.
3. **Validation helpers:** a shared `validate(doc, schema)` in both Py and TS; reject on ingest.
4. **Golden fixtures:** commit 3–5 example documents (small apartment, L-shaped house,
   multi-level) under `packages/schemas/examples/` that validate; use them as test fixtures
   everywhere downstream.
5. **Versioning:** add a top-level `schema_version` to each root doc; document the migration policy.
6. **Geometry invariants doc:** write down the rules (CCW outer ring, integer mm, closed rings,
   non-self-intersecting polygons, walls reference real coordinates) and a `lint_geometry()` check.

---

## Deliverables

- `packages/schemas/*.json` for all entities above + generated Py & TS types.
- `make codegen` is deterministic; CI drift check from Phase 01 guards it.
- Example fixtures that pass validation in both languages.

## Acceptance criteria

- A round-trip test: load each example fixture → validate (Py) → serialize → validate (TS) → equal.
- Editing a schema and forgetting `make codegen` fails CI.
- `lint_geometry()` rejects a self-intersecting polygon and a clockwise outer ring.

## Sources

- JSON Schema 2020-12: https://json-schema.org/
- datamodel-code-generator: https://docs.pydantic.dev/latest/integrations/datamodel_code_generator/
- json-schema-to-typescript: https://github.com/bcherny/json-schema-to-typescript
- Ajv: https://ajv.js.org/

---

## Claude build prompt

> Implement Phase 02 (Domain Model & Schemas) per `plan/phase-02-domain-model.md`. In
> `packages/schemas`, author JSON Schema (draft 2020-12) files for Project, Boundary (with Level,
> Polygon, Ring), ProgramGraph (RoomNode, AdjacencyEdge, an extensible RoomType registry), Plan
> (PlanLevel, Room, Wall, Opening, Fixture, Annotation), RuleSet/Rule, and ValidationReport, using
> `$ref` for shared types and storing all coordinates as integer millimetres. Build a deterministic
> `make codegen` that generates Pydantic v2 models and TypeScript types + Ajv runtime validators
> into `packages/schemas/gen/{python,ts}`. Provide shared `validate()` helpers and a
> `lint_geometry()` invariant checker (CCW outer rings, CW holes, closed non-self-intersecting
> polygons, integer mm). Commit 3–5 example fixtures (small apartment, L-shaped house, two-level
> building) that validate in both languages, and a round-trip test (Python validate → serialize →
> TypeScript validate → deep-equal). Wire the CI drift check so editing a schema without codegen
> fails. Document units, coordinate system, geometry invariants, and the schema-version migration
> policy.
