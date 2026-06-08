# Phase 06 — Program Input: Area-Program Spreadsheet + Adjacency Graph

**Goal:** Let the user specify the **program** — which rooms/spaces are wanted, how many, their
target areas and constraints, and the **adjacency relationships** between them — through **two
interchangeable views of one model**: (a) an **Area Programming spreadsheet** (import/edit/export
Excel) and (b) a node-and-edge **adjacency graph**. Both read and write the same Phase-02
`ProgramGraph`; editing one updates the other. This is the "graph nodes" + the area/space-program
input from the brief and the primary driver of generation.

**Depends on:** Phases 02–04. Tightly related to Phase 15 (which exports the area schedule back to Excel).

> **Why both?** Architects almost always start a project from an **area program / schedule of
> accommodation** in Excel (departments, room names, quantities, target areas, sometimes required
> adjacencies). That spreadsheet *is* the program. The graph is the spatial/relational view of the
> same data. We make the spreadsheet a first-class input so teams can paste in what they already have.

---

## Tasks

1. **Area-Program spreadsheet import (Excel/CSV) — a first-class input**
   - **Upload** `.xlsx`/`.xls`/`.csv` (or paste a table / drag a Google-Sheets export). Parse
     server-side with `openpyxl`/`pandas` (CSV via `pandas`); support multi-sheet workbooks and let
     the user pick the sheet and header row.
   - **Column mapping UI:** detect and map source columns → `RoomNode` fields. Expected/eligible
     columns (all fuzzy-matched, user-confirmable): `department/zone`, `room name/label`, `room type`,
     `quantity/count`, `area target` (+ unit: m²/ft²), `area min`, `level/floor`, `occupancy`,
     `aspect ratio`, `requires window/exterior`, `tags`, and an optional **adjacency column**
     (comma-separated room names or an "adjacency matrix" sheet). Persist the mapping as a reusable
     **import profile** per firm/template (firms reuse the same spreadsheet layout repeatedly).
   - **Type inference:** map free-text room names → the `RoomType` registry via a synonyms table +
     fuzzy match (e.g. "WC"/"toilet"→bathroom, "Mtg Rm"→office/meeting); unmatched rows become a
     custom/extensible type and are flagged for confirmation. Never silently drop a row.
   - **Quantity expansion:** a row with `count=3` becomes 3 `RoomNode`s (or one quantified node the
     generator expands), with stable derived ids (`bedroom-1..3`).
   - **Units & validation on ingest:** convert all areas to integer mm² (per Phase 02), reject
     ambiguous/empty units, sum totals per department and overall, and run the same contradiction/
     budget checks as the graph (see tasks 4–5). Show a **preview/diff table** ("12 rooms, 3
     departments, 248 m² total; 2 rows need a type") before committing.
   - **Round-trip:** re-importing an edited spreadsheet **reconciles** against the existing
     `ProgramGraph` by stable key (department+name+index) — updates changed rows, adds new, marks
     removed — instead of clobbering graph-only edits (adjacencies drawn in the graph view survive).
   - **Export back to Excel:** generate a clean area-program workbook from the current `ProgramGraph`
     (rooms, quantities, target/achieved areas once a Plan exists, departments, adjacency matrix
     sheet), styled with totals/subtotals — the same generator used by Phase 15 schedules. This makes
     the tool a drop-in replacement for the manual area-program spreadsheet.
   - **Templates:** ship a downloadable **Area Program template .xlsx** with the expected columns and
     an example, so users can fill it in offline and upload.

2. **Graph canvas**
   - A node-graph editor (use **React Flow**) where each node is a `RoomNode` and each edge is an
     `AdjacencyEdge`. Drag to connect; click an edge to set its relation
     (adjacent / connected-by-door / open-connection / near / not-adjacent) and weight (priority).
   - Node palette grouped by room category (living, sleeping, service, circulation, wet, outdoor).
   - Auto-layout (dagre/elk) + manual arrangement; mini-map; multi-select; copy/paste.
   - **Spreadsheet ⇆ graph sync:** the Area-Program table (task 1) and this graph are two live views
     of the same `ProgramGraph`. A third **table/grid view** (editable data grid) sits beside the
     graph; edits in any view update the others and re-run validation. The spreadsheet is the
     authoritative *bulk-entry* surface; the graph is the authoritative *adjacency* surface.

3. **Room node properties (inspector)**
   - type, label, count (e.g. "3× bedroom" expands to 3 nodes or a quantified node), level/"any",
     `area_min`/`area_target`, aspect-ratio range, `requires_exterior_wall`, `requires_window`,
     fixed position/lock, tags (public/private/service/wet).
   - Validation hints: total target area vs. available buildable area (from Phase 05) with a live
     "space budget" meter (over-budget warning).

4. **Templates & presets**
   - Starter programs: "2-bed apartment", "3-bed house", "small office", "clinic", etc., that
     populate nodes+edges. Users save their own templates (incl. saved **import profiles** from task 1).
   - Bulk tools: "every bedroom adjacent to a bathroom", "all wet rooms share a plumbing wall".

5. **Derived constraints**
   - Compute an **adjacency matrix** and a **bubble-diagram** preview (force-directed) so users
     see the intended relationships spatially before generating.
   - Detect contradictions (A must be adjacent to B and not-adjacent to B) and unsatisfiable
     degree constraints; surface as fixable warnings.

6. **Code-awareness hints (light touch)**
   - Given the selected jurisdiction (Phase 07), pre-fill minimum areas/dimensions for known room
     types as defaults (e.g. min bedroom area), clearly marked as code-derived and editable.

7. **Persistence**
   - Save as Phase 02 `ProgramGraph` via `PUT /projects/{id}/program` (with `source` + retained
     `import_mapping`/raw-rows for re-reconciliation). Validate references, no dangling edges,
     counts ≥ 1, areas positive. Store the uploaded workbook as an artifact for provenance.

---

## Deliverables

- **Area-Program Excel/CSV import** with sheet/header selection, fuzzy column mapping, reusable
  import profiles, room-type inference, quantity expansion, unit conversion, and a preview/diff before commit.
- **Excel export** of the area program (+ downloadable template workbook) and round-trip reconciliation.
- Three synced views of one `ProgramGraph`: spreadsheet/grid, adjacency graph, bubble diagram —
  with templates, an adjacency matrix view, and a live space-budget meter.
- Contradiction detection with actionable warnings.

## Acceptance criteria

- Uploading a sample area-program `.xlsx` (departments, room names, counts, target areas in m²)
  yields a valid `ProgramGraph` with correct integer-mm² areas, quantities expanded, and types
  inferred; ambiguous rows are flagged, never dropped.
- Editing the imported program in the graph view (e.g. drawing adjacencies), then re-uploading an
  updated spreadsheet, reconciles by stable key and **preserves the graph-only adjacency edits**.
- Exporting the program to Excel reproduces the rooms/quantities/areas/departments and an adjacency
  sheet; re-importing that export is a no-op (round-trip stable).
- A "3-bed house" template generates the expected nodes/edges and validates.
- Setting bedroom count to 3 yields three solvable bedroom nodes (or a quantified node the
  generator expands).
- The space-budget meter turns red when target areas exceed the buildable envelope.
- Contradictory constraints are detected and reported before generation is allowed.

## Sources

- openpyxl (read/write .xlsx): https://openpyxl.readthedocs.io/  · pandas IO: https://pandas.pydata.org/docs/user_guide/io.html
- Fuzzy column/name matching: https://github.com/rapidfuzz/RapidFuzz
- SheetJS (optional client-side xlsx parse/preview): https://sheetjs.com/
- React Flow: https://reactflow.dev/  · dagre layout: https://github.com/dagrejs/dagre
- elkjs: https://github.com/kieler/elkjs
- Architectural bubble diagrams / schedule of accommodation (concept): https://en.wikipedia.org/wiki/Bubble_diagram

---

## Claude build prompt

> Implement Phase 06 (Program Input: Area-Program Spreadsheet + Adjacency Graph) per
> `plan/phase-06-room-graph-input.md`. Build the **Area-Program Excel/CSV import** as a first-class
> input: upload `.xlsx`/`.xls`/`.csv` (or paste a table), parse server-side with openpyxl/pandas with
> sheet + header-row selection, and a fuzzy column-mapping UI (RapidFuzz) mapping source columns →
> RoomNode fields (department, room name, type, quantity, area target+unit, area min, level,
> occupancy, aspect, requires-window, tags, and an adjacency column or matrix sheet) with reusable
> per-firm **import profiles**. Infer RoomType from free-text room names via a synonyms+fuzzy table
> (flagging, never dropping, unmatched rows), expand `count` into stable-id RoomNodes, convert all
> areas to integer mm² rejecting ambiguous units, and show a preview/diff (room/department/total
> counts, rows needing attention) before commit. Support **round-trip reconciliation** (re-importing
> an edited sheet updates/adds/marks-removed by stable key while preserving graph-only adjacency
> edits), **Excel export** of the area program (rooms, quantities, target/achieved areas, departments,
> adjacency-matrix sheet, totals) sharing the Phase-15 schedule generator, and a downloadable Area
> Program template workbook. Then build the React Flow node-graph editor (RoomNodes + AdjacencyEdges,
> drag-to-connect, per-edge relation+weight, categorized palette, auto-layout, mini-map, multi-select,
> copy/paste) plus an editable grid/table view, all as **three synced views of one ProgramGraph**
> (edit any → others + validation update). Add the room-node inspector (type, label, count, level,
> area_min/target, aspect, requires_exterior_wall/window, fixed position/lock, tags) with a live
> space-budget meter vs. the Phase-05 buildable area; starter templates (2-bed apartment, 3-bed house,
> small office, clinic) and bulk rules; a derived adjacency matrix + bubble-diagram preview; and
> contradiction/unsatisfiable-constraint detection. When a jurisdiction is selected, pre-fill
> code-derived minimum areas as editable defaults. Persist as the Phase-02 ProgramGraph via
> `PUT /projects/{id}/program` retaining `source` + import mapping/raw rows and storing the uploaded
> workbook as a provenance artifact, with reference/value validation. Acceptance: a sample area-program
> .xlsx imports to a valid ProgramGraph with correct mm² areas, expanded quantities, and inferred
> types (ambiguous rows flagged); graph-only adjacency edits survive a spreadsheet re-import; Excel
> export round-trips with no-op re-import; the 3-bed template validates; bedroom count 3 yields three
> solvable nodes; the budget meter flags over-area programs; and contradictions block generation.
