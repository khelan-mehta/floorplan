# Phase 15 — Export to DWG / IFC (Revit-ready deliverables)

**Goal:** Export the chosen `Plan` to the formats architects need: **DWG** (2D drawing deliverable,
the brief's explicit requirement) and **IFC4** (BIM model for Revit). Exports must carry layers,
storeys, room/space data, and dimensions so the receiving tool can continue the work.

**Depends on:** Phases 02, 10, 11, 12. Feeds Phase 16 (Revit).

> Two interchange paths: **DWG/DXF** = 2D documentation; **IFC** = the intelligent 3D model. Revit
> imports DWG as drafting/underlay and **links/opens IFC as a model**. Provide both.

---

## Tasks

1. **DXF/DWG export (`services/export`, ezdxf + ODA)**
   - Build a DXF document from the `Plan`: walls (as polylines/hatched solids or wall lines),
     doors/windows as blocks (`INSERT` of door/window block definitions with attributes), room
     boundaries + **room tags** (name, area) as MTEXT, dimensions, grids, and a title block.
   - **Layering convention**: follow a standard (AIA / ISO 13567 / NCS) — e.g. `A-WALL`, `A-DOOR`,
     `A-GLAZ`, `A-AREA`, `A-FLOR`, `A-ANNO-DIMS`, `A-ANNO-TEXT`; configurable layer mapping.
   - Multi-level → one DXF per storey or a single file with layers/blocks per storey; consistent
     world units (mm) and correct scale.
   - Convert DXF→DWG via the **ODA File Converter** add-on (target a Revit-friendly version, e.g.
     AutoCAD 2018). Validate the round-trip opens cleanly.

2. **IFC4 export (`ifcopenshell`)**
   - Author a proper spatial hierarchy: `IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey →
     elements`. Map model elements: walls→`IfcWallStandardCase`, slabs→`IfcSlab`, doors→`IfcDoor`,
     windows→`IfcWindow`, stairs→`IfcStair`, furniture→`IfcFurniture`/`IfcSanitaryTerminal`, and
     rooms→`IfcSpace` with name/number/area properties.
   - Attach property sets (Psets) incl. areas, room data, and our metadata; correct units, placement,
     and geometry (extruded solids with openings as `IfcOpeningElement` voiding walls).
   - Use the **semantic tags** from Phase 11 to map each 3D solid to the right IFC entity.
   - Validate against the IFC4 schema (ifcopenshell validation / IfcOpenShell `ifcconvert`).

3. **Export options & jobs**
   - `POST /plans/{id}/export?format=dwg|dxf|ifc|glb|pdf` (async job, artifacts to object storage).
   - Options: which levels, layer standard, units, include furniture, include code-flags as a layer,
     paper size/scale for PDF sheets.
   - **PDF/print sheets**: composed drawing sheets (plan per level, title block, dimensions, room
     schedule) for client packets.

4. **Schedules & data export**
   - Room/area schedule (CSV/XLSX), door/window schedule, component/material takeoff — derived from
     the Plan, matching what shows in the DWG/IFC. The room/area schedule **reuses the Phase-06
     area-program workbook generator** and includes target vs. **achieved** areas (program intent vs.
     generated result) so architects can reconcile the delivered plan against the original Excel input.

5. **Fidelity tests**
   - Golden exports: known plan → expected DXF entities on expected layers; IFC with expected entity
     counts and spatial structure; geometry re-imported and compared within tolerance.

---

## Deliverables

- DWG/DXF export with proper layers, blocks, room tags, dimensions, and title block.
- IFC4 export with correct spatial hierarchy, element types, spaces, Psets, and openings.
- PDF sheet sets + room/door/component schedules.
- Async export jobs with options; artifacts stored and downloadable.

## Acceptance criteria

- Exported DWG opens in AutoCAD/Revit with walls/doors/windows/rooms on the correct layers and
  correct real-world dimensions (a 10 m wall measures 10 m).
- Exported IFC opens in a viewer and Revit showing the correct storeys, walls with door/window
  openings, and `IfcSpace`s with areas; ifcopenshell validation passes.
- Door/window blocks in DWG and `IfcDoor`/`IfcWindow` in IFC match the plan counts.
- Schedules match the model (room count/areas reconcile with the validator's numbers).

## Sources

- ezdxf: https://ezdxf.readthedocs.io/  · ODA File Converter add-on: https://ezdxf.readthedocs.io/en/stable/addons/odafc.html
- IfcOpenShell: https://ifcopenshell.org/  · IFC4 schema: https://standards.buildingsmart.org/IFC/RELEASE/IFC4/
- AIA CAD layer standard / ISO 13567: https://www.nationalcadstandard.org/
- web-ifc (browser-side IFC, optional client export): https://github.com/ThatOpen/engine_web-ifc

---

## Claude build prompt

> Implement Phase 15 (Export to DWG/IFC) per `plan/phase-15-export-dwg-ifc.md` in `services/export`.
> DXF/DWG: build a DXF from a Phase-02 Plan with ezdxf — walls, door/window block INSERTs with
> attributes, room boundaries with name/area MTEXT tags, dimensions, grids, and a title block — on a
> configurable AIA/ISO-13567 layer standard (A-WALL/A-DOOR/A-GLAZ/A-AREA/A-ANNO-*), in mm at correct
> scale, one file per storey or layered single file, then convert DXF→DWG via the ODA File Converter
> add-on targeting AutoCAD 2018. IFC4: author with ifcopenshell a full IfcProject→IfcSite→IfcBuilding
> →IfcBuildingStorey hierarchy mapping the Phase-11 semantically-tagged solids to IfcWallStandardCase/
> IfcSlab/IfcDoor/IfcWindow/IfcStair/IfcFurniture/IfcSanitaryTerminal and rooms to IfcSpace with
> area/number Psets, with openings as IfcOpeningElement voiding walls, correct units/placement, and
> schema validation. Add `POST /plans/{id}/export?format=dwg|dxf|ifc|glb|pdf` async jobs with options
> (levels, layer standard, units, include furniture, include code-flags layer, paper size/scale),
> composed PDF sheet sets (plan per level + title block + room schedule), and room/door/component
> schedules as CSV/XLSX. Add golden-export fidelity tests (expected DXF entities per layer; expected
> IFC entity counts and spatial structure; re-import geometry compared within tolerance). Acceptance:
> the DWG opens in AutoCAD/Revit with elements on correct layers and a 10 m wall measuring 10 m, the
> IFC opens in Revit/a viewer with correct storeys, openings, and IfcSpaces with areas and passes
> ifcopenshell validation, block/entity counts match the plan, and schedules reconcile with the
> validator's areas.
