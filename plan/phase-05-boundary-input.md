# Phase 05 — Boundary Input (the outer geometry of the floor)

**Goal:** Let users define the buildable space: draw or import the outer floor outline per level,
set the site parcel + setbacks, north angle, floor-to-floor heights, fixed cores, and voids. This
is the spatial container the generator fills.

**Depends on:** Phases 02–04.

---

## Tasks

1. **Boundary drawing tools (2D editor)**
   - Polygon draw with click-to-add vertices, ortho/snap-to-grid, snap-to-angle (0/45/90°),
     and snap-to-existing-vertex. Edit: drag vertices/edges, add/remove vertices, fillet corners.
   - Numeric entry: type a length/angle while drawing an edge (CAD-style precise input).
   - Holes (courtyards/voids) and multiple disjoint outlines per level.
   - Live readout: area, perimeter, bounding box; warnings for self-intersection (uses
     `lint_geometry` from Phase 02).

2. **Import paths**
   - **DXF/DWG import:** parse with `ezdxf` server-side (DWG via ODA→DXF); extract closed
     polylines on a chosen layer as the outline. Let the user pick which layer/entity is the
     boundary and set the unit/scale.
   - **Image trace:** upload a site plan/sketch image, set scale by drawing a known dimension,
     trace the outline (manual polygon over the image, optional auto-edge assist).
   - **GeoJSON/parcel import** for the site polygon (optional).

3. **Levels**
   - Add/remove levels, set `elevation`, `floor_to_floor`, copy outline from another level.
   - Per-level cores (stair/lift/shaft footprints) that the generator must preserve and route to.

4. **Site & setbacks**
   - Draw the parcel polygon; set front/rear/side setbacks (mm). Compute and display the
     **buildable envelope** = parcel inset by setbacks ∩ outline. Generator must stay inside it.
   - North angle control (affects daylight/orientation rules in Phase 09).

5. **Persistence & validation**
   - Save as the Phase 02 `Boundary` via `PUT /projects/{id}/boundary`.
   - Validate: closed rings, min area, setback compliance, no overlapping levels' cores, units set.

6. **3D preview**
   - Extrude each level outline by floor-to-floor to show the massing volume in the 3D viewport,
     with setback envelope ghosted — instant feedback that the container is correct.

---

## Deliverables

- A complete boundary editor producing a valid `Boundary` for single- and multi-level buildings.
- DXF/DWG and image-trace import paths working on real sample files.
- 3D massing preview of the empty building.

## Acceptance criteria

- Drawing a 10m×8m rectangle reads exactly 80 m² and stores integer-mm coordinates.
- Importing a sample DWG yields a boundary within tolerance of the source geometry.
- Setbacks correctly shrink the buildable envelope; violations are flagged before generation.
- Round-trips through the API and re-renders identically on reload.

## Sources

- ezdxf import/layers: https://ezdxf.readthedocs.io/en/stable/
- ODA File Converter (DWG↔DXF): https://www.opendesign.com/guestfiles/oda_file_converter
- shapely (area, buffer/inset, validity): https://shapely.readthedocs.io/
- Konva transforms/snapping: https://konvajs.org/docs/

---

## Claude build prompt

> Implement Phase 05 (Boundary Input) per `plan/phase-05-boundary-input.md`. In the 2D editor
> (Phase 04 Konva stage), build polygon drawing with grid/angle/vertex snapping, CAD-style numeric
> length/angle entry, vertex/edge editing, holes, and multiple outlines per level, with live
> area/perimeter readouts and self-intersection warnings via `lint_geometry`. Add a multi-level
> manager (elevation, floor-to-floor, copy outline, per-level cores/voids). Add a site/setback tool
> that draws the parcel, applies front/rear/side setbacks, computes the buildable envelope (parcel
> inset ∩ outline), and a north-angle control. Implement import paths: server-side DXF/DWG parsing
> with ezdxf (DWG via ODA→DXF) with a layer/unit picker that extracts closed polylines as the
> outline, plus an image-trace flow (upload, set scale by a known dimension, trace polygon over the
> image). Persist as the Phase 02 Boundary via `PUT /projects/{id}/boundary` with full validation
> (closed rings, min area, setback compliance, units required). Show a 3D massing preview by
> extruding level outlines with the setback envelope ghosted. Acceptance: a 10×8 m rectangle reads
> 80 m² in integer mm, a sample DWG imports within tolerance, setbacks shrink the envelope, and the
> boundary round-trips through the API unchanged.
