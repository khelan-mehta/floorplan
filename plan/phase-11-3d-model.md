# Phase 11 — 3D Model Generation

**Goal:** Turn a 2D `Plan` into a real 3D building model — extruded walls with openings cut, floor
and ceiling slabs, doors/windows as 3D objects, stairs, and optional roof — tessellated to glTF for
the web viewport and structured for IFC export (Phase 15).

**Depends on:** Phases 02, 08, 10. Feeds Phases 13, 14, 15.

---

## Tasks

1. **Solidification (`services/geometry`, deterministic)**
   - Walls: sweep each wall centerline by thickness × height into a solid; **boolean-subtract**
     openings (door/window voids) using CSG. Resolve wall joins/corners cleanly (miter/butt).
   - Slabs: floor slab = level outline minus voids; ceiling/next-floor slab; slab thickness from
     settings. Stack levels by `floor_to_floor`.
   - Openings: insert parametric door/window frame+leaf/glazing solids into the cut voids.
   - Stairs: generate tread/riser geometry between levels from stair footprints + rise/run.
   - Optional roof: flat/gable/hip from outline + parameters.
   - Keep a **semantic tag on every solid** (element id, type, level, room/wall/opening ref) so
     IFC export can map solids → IfcWall/IfcSlab/IfcDoor/etc.

2. **Tessellation & delivery**
   - Produce **glTF/GLB** (Draco-compressed) with a node hierarchy mirroring the model
     (Site→Building→Storey→element) and material assignments by element type.
   - Generate per-level and whole-building variants; stream via object storage URLs (Phase 03).

3. **Web rendering (R3F)**
   - Load the glTF into the Phase-04 3D viewport with proper materials, shadows, and section
     planes (cut the model at any height to see plan-as-3D). Level isolation (show one storey).
   - Camera bookmarks (iso, top, per-room interior). Click a 3D element → select the same entity
     in 2D (shared selection state).

4. **Performance**
   - Instancing for repeated components (doors, windows, furniture); LOD; frustum culling; lazy
     per-storey loading for large buildings.

5. **Consistency guarantee**
   - The 3D model is a pure function of the `Plan` (+ settings). Re-solidifying an unchanged plan
     yields identical geometry (hash-stable) for caching.

---

## Deliverables

- `geometry` service: `Plan → 3D solids (semantically tagged) → glTF/GLB`.
- 3D viewport renders walls/openings/slabs/stairs with section planes and storey isolation.
- Shared selection between 2D and 3D.

## Acceptance criteria

- A door opening is a real hole through the wall solid (verified by section cut), not a decal.
- Multi-level plans stack correctly with slabs and aligned stairs.
- Every solid carries its element id/type; a generated glTF node tree matches Site/Building/Storey.
- Re-solidifying an unchanged plan produces a byte-identical GLB (caching works).
- The example building renders at ≥30fps with section planes active.

## Sources

- three.js / R3F: https://threejs.org/ · https://r3f.docs.pmnd.rs/
- three-bvh-csg (boolean ops): https://github.com/gkjohnson/three-bvh-csg
- Server-side CSG/mesh: trimesh https://trimesh.org/ , manifold https://github.com/elalish/manifold
- glTF + Draco: https://www.khronos.org/gltf/ · https://google.github.io/draco/
- pygltflib: https://gitlab.com/dodgyville/pygltflib

---

## Claude build prompt

> Implement Phase 11 (3D Model Generation) per `plan/phase-11-3d-model.md`. In a deterministic
> `services/geometry`, solidify a Phase-02 Plan: sweep wall centerlines by thickness×height into
> solids and boolean-subtract door/window voids (CSG), resolve corner joins, build floor/ceiling
> slabs per level (outline minus voids) stacked by floor_to_floor, insert parametric door/window
> frame+glazing solids into the voids, generate stair tread/riser geometry between levels, and
> optionally a flat/gable/hip roof — tagging every solid with its element id/type/level/ref. Export
> Draco-compressed glTF/GLB with a Site→Building→Storey→element node hierarchy and per-type
> materials, in per-level and whole-building variants delivered via object-storage URLs. Load these
> into the Phase-04 R3F viewport with materials, shadows, section planes (horizontal cut at any
> height), storey isolation, camera bookmarks, and click-to-select that shares selection state with
> the 2D editor. Optimize with instancing of repeated components, LOD, culling, and lazy per-storey
> loading. Guarantee the model is a pure function of the Plan so re-solidifying an unchanged plan
> yields a byte-identical GLB for caching. Acceptance: a door is a real hole through the wall (verify
> by section cut), multi-level plans stack with aligned stairs and slabs, every solid carries its
> id/type, the glTF node tree matches Site/Building/Storey, unchanged plans re-solidify identically,
> and the example building renders ≥30fps with section planes active.
