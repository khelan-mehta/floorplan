# Phase 12 — Component & Interior Library

**Goal:** A catalog of reusable, parametric interior components — furniture, fixtures, sanitary,
appliances, joinery, doors/windows families — plus placement rules so rooms can be auto-furnished
and users can swap/edit interiors. This is the "library of components of all different interiors
possible" from the brief.

**Depends on:** Phases 02, 11. Used by Phases 13 (placement/swap) and 15 (export).

---

## Tasks

1. **Component model & registry**
   - A `Component` schema (extends Phase 02): id, category (seating, bed, table, storage,
     sanitary, kitchen, appliance, door, window, lighting, plant…), tags, **parameters** (width/
     depth/height, finish, count), bounding box, clearance zones, anchor/snap points, mount type
     (floor/wall/ceiling), price/metadata, and references to **3D asset** (glTF) + **2D symbol** +
     **IFC mapping** (IfcFurniture, IfcSanitaryTerminal, IfcDoor…).
   - Store assets in object storage; registry in DB; a versioned catalog with categories/search.

2. **Parametric components**
   - Components can be **procedural** (generated from parameters, e.g. a parametric kitchen run,
     wardrobe, staircase, modular sofa) or **static glTF** assets. Provide a small procedural
     toolkit (box/extrude/array primitives) for parametric families.
   - Each component declares **clearance/keep-out zones** (e.g. 600mm in front of a toilet, door
     swing) used by placement and validation.

3. **Placement rules & auto-furnish**
   - Per `RoomType`, define **layout rules**: required components (bed in bedroom, WC+basin in
     bathroom, counter+sink+stove in kitchen), preferred wall/anchor, spacing, against-wall vs.
     centered, circulation clearance. An **auto-furnish** pass populates a room respecting
     clearances and the room polygon.
   - Style packs / "interior themes" (minimal, classic, office, hospitality) that select a coherent
     set of components and finishes.

4. **Catalog UI**
   - Browsable, searchable, filterable library panel with 3D thumbnails; drag-into-room placement;
     favorites; per-project palette. Admin tools to upload/curate components and edit metadata.

5. **Validation integration**
   - Placement respects clearance zones and room bounds; collisions and blocked-egress placements
     are flagged (feeds Phase 09 metrics like circulation/clearance).

6. **Seed catalog**
   - Ship a starter catalog covering residential + light commercial (≥60 components across
     categories) with glTF assets, 2D symbols, and IFC mappings, so downstream phases have content.

---

## Deliverables

- Component schema + registry + object-storage assets + searchable catalog UI.
- Procedural component toolkit + ≥5 parametric families.
- Per-room-type placement rules + an auto-furnish pass.
- Seed catalog (≥60 components) with 3D/2D/IFC representations.

## Acceptance criteria

- Auto-furnishing a bedroom places a bed + side tables + wardrobe within bounds and clearances.
- A bathroom auto-furnish places WC/basin/shower honoring fixture clearances; a collision is flagged.
- Swapping a component (Phase 13) preserves anchor/clearance and updates 2D, 3D, and IFC mapping.
- A parametric kitchen run adapts to a wall length change without manual asset edits.

## Sources

- glTF asset pipeline: https://www.khronos.org/gltf/
- IFC product types (IfcFurniture, IfcSanitaryTerminal, IfcDoor): https://standards.buildingsmart.org/IFC/RELEASE/IFC4/
- Furniture clearance standards (e.g. NKBA kitchen/bath guidelines): https://nkba.org/
- Accessibility clearances (ADA/Part M): https://www.ada.gov/

---

## Claude build prompt

> Implement Phase 12 (Component & Interior Library) per `plan/phase-12-component-library.md`. Define
> a Component schema extending Phase 02 (category, tags, parameters, bbox, clearance/keep-out zones,
> anchor/snap points, mount type, metadata, and references to a glTF asset, a 2D symbol, and an IFC
> product mapping) and a versioned DB registry with object-storage assets and category/tag search.
> Support both static glTF components and procedural/parametric families via a small toolkit
> (box/extrude/array), shipping ≥5 parametric families (e.g. kitchen run, wardrobe, modular sofa,
> shelving, stair). Define per-RoomType placement/layout rules (required components, preferred
> wall/anchor, spacing, clearances) and an auto-furnish pass that populates a room respecting
> clearances and room bounds, plus interior "style packs". Build a searchable/filterable catalog UI
> panel with 3D thumbnails, drag-into-room placement, favorites, and a per-project palette, with
> admin upload/curation. Integrate clearance/collision/egress checks feeding the Phase-09 metrics.
> Ship a seed catalog of ≥60 residential + light-commercial components each with glTF, 2D symbol,
> and IFC mapping. Acceptance: auto-furnishing a bedroom and a bathroom places the expected fixtures
> within bounds and clearances (flagging collisions), swapping a component preserves anchor/clearance
> across 2D/3D/IFC, and a parametric kitchen adapts to a wall-length change automatically.
