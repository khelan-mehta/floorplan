# Phase 13 — Interactive Editing (swap rooms, change types, edit interiors)

**Goal:** The high-level, "design-y" editing the brief calls for: change a room's type, swap one
room layout for another, swap/move/replace interior components, and re-flow the plan — all on the
web app, with live validation, on both 2D and 3D. This sits on top of Phases 10 (2D geometry edits)
and 12 (components).

**Depends on:** Phases 09, 10, 11, 12.

---

## Tasks

1. **Change room type**
   - Convert a room to another type; re-tag, recolor, re-apply that type's placement rules and code
     constraints; optionally auto-refurnish. Re-validate (areas/daylight/egress may change).

2. **Swap room layout / template**
   - Offer alternative interior layouts for the same room (e.g. 3 bathroom arrangements, 2 kitchen
     configs) from the library/generator; preview and apply, keeping the room boundary fixed.
   - "Regenerate this room only" — re-run the generator scoped to one room/zone, leaving the rest.

3. **Swap & edit interiors**
   - Select a fixture → swap with a compatible component (same category/anchor) via the catalog;
     move/rotate/scale with snapping to walls, room, and other fixtures; clearance-aware drag.
   - Bulk operations: replace all instances of a component, restyle a room (apply a style pack).

4. **Move walls / resize rooms (semantic)**
   - Push/pull a wall and have neighboring rooms reflow; "swap two rooms" (exchange their footprints
     and contents); split/merge rooms with content reconciliation.

5. **Local regeneration & suggestions**
   - "Suggest improvements" runs the validator and proposes targeted fixes (widen a door, enlarge a
     room by stealing from an oversized neighbor) as one-click actions.

6. **Everything live + versioned**
   - Each semantic edit is a command (undo/redo), re-validates (debounced, Phase 09), updates 2D +
     3D, and checkpoints a Plan version (Phase 03). Selection is shared across 2D/3D/inspector.

---

## Deliverables

- Room-type change, layout swap, scoped regeneration, component swap/move, semantic wall edits,
  and one-click fix suggestions — all live across 2D and 3D with undo/redo and versioning.

## Acceptance criteria

- Changing a "bedroom" to "office" recolors, re-furnishes, and re-validates against office rules.
- Swapping a bathroom layout keeps the room boundary and updates fixtures in 2D, 3D, and the IFC map.
- "Regenerate this room only" changes just that room; the rest of the plan is untouched.
- A flagged narrow door offers a "widen to compliant width" one-click fix that clears the flag.
- Every action is undoable and produces a new Plan version; 2D and 3D stay in sync.

## Sources

- Command pattern / undo: https://refactoring.guru/design-patterns/command
- Constraint-based reflow: https://en.wikipedia.org/wiki/Geometric_constraint_solving
- (Generator scoping reuses Phase 08; validation reuses Phase 09; components reuse Phase 12.)

---

## Claude build prompt

> Implement Phase 13 (Interactive Editing) per `plan/phase-13-interactive-editing.md` on top of
> Phases 10–12. Add change-room-type (re-tag/recolor, re-apply placement rules + code constraints,
> optional auto-refurnish, re-validate), swap-room-layout (offer alternative interior layouts from
> the library/generator for a fixed room boundary, preview+apply) and "regenerate this room only"
> (scoped generator run leaving the rest of the plan untouched). Add interior editing: select a
> fixture and swap with a compatible component via the catalog, clearance-aware move/rotate/scale
> with snapping to walls/room/other fixtures, bulk replace-all, and apply-style-pack. Add semantic
> geometry edits: push/pull a wall with neighbor reflow, swap two rooms' footprints+contents, and
> split/merge with content reconciliation. Add a "suggest improvements" action that runs the Phase-09
> validator and offers one-click targeted fixes (widen door, enlarge a room from an oversized
> neighbor). Make every edit a command with undo/redo, debounced re-validation, synchronized 2D+3D
> updates, shared selection, and a checkpointed Plan version via the Phase-03 API. Acceptance:
> bedroom→office recolors/refurnishes/re-validates against office rules, a bathroom layout swap keeps
> the boundary and updates 2D/3D/IFC, scoped room regeneration leaves the rest untouched, a narrow-
> door fix clears its flag in one click, and all actions are undoable and versioned with 2D/3D in sync.
