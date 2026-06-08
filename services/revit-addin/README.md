# Revit Interoperability (Phase 16)

Two interchange paths from the Studio to Autodesk Revit:

1. **IFC4 (primary, no plugin)** — `POST /plans/{id}/export?format=ifc` produces an IFC tuned for
   Revit native-category import (see mapping below). This is 80% of the value with zero install.
2. **DWG underlay** — `?format=dxf` produces 2D drawings to draft over (DWG via the ODA converter).
3. **Optional add-in / Dynamo** — one-click import of an approved plan as native Revit elements,
   for teams that want it (scaffold in this folder).

> Status: the IFC/DXF exporters are implemented + tested (`services/export`). The C# add-in and
> Dynamo graph here are **authored but not compiled** (no Revit/.NET on the dev machine) — they are
> the integration scaffold to build against Revit 2023–2025.

## IFC import procedure (no plugin)

- **Link IFC** (`Insert → Link IFC`) to keep the model referenced, or **Open IFC** to convert to
  native elements. Use the import mapping file `RevitIfcImport.txt` (this folder) so categories map
  correctly. Levels come from `IfcBuildingStorey`; Rooms from `IfcSpace` (with NetFloorArea).

## Element mapping spec (Studio → IFC → Revit)

| Studio (Plan) | IFC4 entity | Revit category |
|---------------|-------------|----------------|
| `Room`        | `IfcSpace` (+ `Qto_SpaceBaseQuantities.NetFloorArea`) | Rooms |
| `Wall`        | `IfcWall` (`IfcExtrudedAreaSolid`) | Walls |
| `Opening` kind=door | `IfcDoor` (`OverallWidth/Height`) | Doors |
| `Opening` kind=window | `IfcWindow` (`OverallWidth/Height`) | Windows |
| level | `IfcBuildingStorey` | Levels |
| `Fixture` (Phase 12) | `IfcFurniture`/`IfcSanitaryTerminal` (follow-up) | Furniture / Plumbing Fixtures |

Follow-ups: `IfcOpeningElement` voids cutting walls (so doors/windows host into walls), slab
geometry on `IfcSlab`, stairs, and Fixture→IFC mapping.

## Verification checklist (run in Revit per release)

- [ ] Link/Open the exported IFC → Levels match plan levels.
- [ ] Walls appear in the Walls category at correct lengths (a 10 m wall measures 10 m).
- [ ] Doors/Windows appear in their categories.
- [ ] Rooms (from IfcSpace) carry name + area within tolerance of the room schedule CSV.
- [ ] DWG underlay aligns + measures correctly in a drafting view.
