# Phase 16 — Revit Interoperability

**Goal:** Make the handoff to **Autodesk Revit** smooth and, ideally, round-trippable: validated IFC
import, a documented mapping so Revit elements come in as native categories, and an optional Revit
add-in / Dynamo workflow that imports our model (and can push changes back). This closes the brief's
"they further use this on Revit" loop.

**Depends on:** Phase 15 (IFC/DWG export).

> Reality check: Revit ingests IFC and DWG natively, so a **high-quality IFC is 80% of the value**
> with zero plugin install. The add-in is an enhancement for teams that want one-click + roundtrip.

---

## Tasks

1. **IFC import quality (no plugin)**
   - Tune the Phase-15 IFC so Revit's IFC importer maps elements to native categories: walls→Walls,
     doors→Doors, windows→Windows, slabs→Floors, stairs→Stairs, spaces→Rooms, furniture→Furniture.
   - Provide a **Revit IFC import settings template** (`.txt` mapping file / import config) and a
     documented procedure (Open IFC vs. Link IFC) so areas/rooms and levels come through correctly.
   - Verify levels↔`IfcBuildingStorey`, room areas↔Revit Rooms, and that wall/opening hosting works.

2. **DWG as underlay**
   - Ensure the Phase-15 DWG imports as a clean 2D underlay (correct layers/units) for teams that
     draft over it in Revit.

3. **Optional Revit add-in (C#, Revit API)**
   - A `.addin` + ribbon button "Import from FloorPlan Studio": authenticates, lists the user's
     approved plans, downloads the IFC/our JSON, and builds native Revit elements (walls by
     type, hosted doors/windows, floors, rooms with names/areas) via the **Revit API**.
   - **Roundtrip (stretch):** read back edits made in Revit and POST a diff to our API to keep the
     web project in sync (or at least re-import as a new version).
   - Distribute as an installer; document Revit version support (e.g. 2023–2025) and API constraints.

4. **Dynamo alternative**
   - A **Dynamo** graph (lower effort than a full add-in) that reads our JSON/IFC and places
     elements — good for firms that prefer visual scripting and avoids C# build/distribution.

5. **Mapping spec & validation**
   - A written **element-mapping spec** (our Plan/IFC entity → Revit category + parameters) kept in
     sync with Phase 02/15. A test checklist run in Revit for each release (import → verify
     categories, levels, rooms, schedules).

6. **Family mapping for components**
   - Map our component library (Phase 12) to Revit **families** where possible (or generic models),
     so furnished plans bring furniture/fixtures in as usable families.

---

## Deliverables

- A tuned IFC + documented Revit import procedure and settings template giving native-category import.
- A DWG underlay verified in Revit.
- (Optional) A Revit add-in and/or Dynamo graph that builds native elements from our data.
- An element-mapping spec + a Revit verification checklist.

## Acceptance criteria

- Linking/opening the exported IFC in Revit yields native Walls/Doors/Windows/Floors/Stairs/Rooms
  on the correct Levels, with room areas matching our schedule within tolerance.
- The DWG underlay aligns and measures correctly in a Revit drafting view.
- (If built) the add-in imports an approved plan and creates hosted doors/windows in walls in one
  click against a supported Revit version.
- The mapping checklist passes for the example building.

## Sources

- Revit IFC import/Open vs Link: https://www.autodesk.com/support/technical/ (IFC import)
- buildingSMART IFC↔Revit: https://standards.buildingsmart.org/IFC/RELEASE/IFC4/
- Revit API: https://www.revitapidocs.com/  · Dynamo: https://dynamobim.org/
- Revit IFC open-source exporter/importer: https://github.com/Autodesk/revit-ifc
- DataDrivenConstruction CAD/Revit/IFC converters: https://github.com/datadrivenconstruction/cad2data-Revit-IFC-DWG-DGN

---

## Claude build prompt

> Implement Phase 16 (Revit Interoperability) per `plan/phase-16-revit-integration.md`. First,
> without any plugin, tune the Phase-15 IFC so Revit's importer maps elements to native categories
> (walls→Walls, doors→Doors, windows→Windows, slabs→Floors, stairs→Stairs, IfcSpace→Rooms,
> furniture→Furniture), provide a Revit IFC import-settings/mapping template and a documented
> Open-vs-Link procedure, and verify Levels↔IfcBuildingStorey, room areas↔Revit Rooms, and
> wall/opening hosting. Verify the Phase-15 DWG imports as a clean, correctly-scaled 2D underlay.
> Then build an OPTIONAL Revit add-in (C#, Revit API 2023–2025) with a ribbon button that
> authenticates, lists the user's approved plans, downloads our IFC/JSON, and creates native walls
> (by type), hosted doors/windows, floors, stairs, and rooms with names/areas — plus a stretch
> roundtrip that reads Revit edits and POSTs a diff/new version to our API; also provide a Dynamo
> graph alternative that places elements from our JSON/IFC. Write an element-mapping spec (Plan/IFC
> entity → Revit category + parameters) kept in sync with Phases 02/15, map the Phase-12 component
> library to Revit families/generic models, and a Revit verification checklist. Acceptance: linking
> the IFC in Revit produces native categories on correct Levels with matching room areas, the DWG
> underlay aligns and measures correctly, and (if built) the add-in one-click imports an approved
> plan creating hosted openings against a supported Revit version.
