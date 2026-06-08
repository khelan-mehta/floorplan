# Phase 10 — 2D Plan Editor (render + edit)

**Goal:** A precise, CAD-grade 2D editor to view and modify generated plans: walls, rooms, doors,
windows, dimensions, and room tags — with snapping, measurement, and live validation feedback.

**Depends on:** Phases 04, 08, 09. Pairs with Phase 13 (semantic edits) and Phase 11 (3D).

---

## Tasks

1. **Rendering**
   - Draw the active level: room fills (color by type + legend), walls (true thickness with proper
     joins/miters), door/window symbols (swing arcs, sills), stairs, fixtures (Phase 12), and a
     dimension/annotation layer. Layer toggles (rooms / walls / dims / furniture / grid / code-flags).
   - Pan/zoom, snap grid, rulers, scale bar; print/PDF-accurate scaling (1:50, 1:100).

2. **Editing tools**
   - **Wall:** draw, split, join, drag (with attached rooms reflowing), set thickness/type, align.
   - **Room:** reshape polygon (drag edges/vertices), split a room, merge rooms, set type, label,
     resize numerically (type a target area/dimension and let it solve the edge move).
   - **Opening:** place/move doors & windows along walls with offset snapping; set width/height/
     swing; auto-host to the wall (move the wall → opening follows).
   - **Dimension:** linear/aligned/angular dimensions, auto-dimension a room, editable text.

3. **Snapping & constraints engine**
   - Snap to grid, endpoints, midpoints, perpendicular, extension, parallel; ortho lock; numeric
     override. Keep walls connected (a shared corner moves both walls). Maintain geometry
     invariants from Phase 02 on every edit.

4. **Live validation overlay**
   - On edit (debounced), call the `validate` service; render code flags inline (red/amber badges
     on offending rooms/doors) with hover-to-see citation + fix hint. A side panel lists all issues
     with click-to-zoom.

5. **Undo/redo & history**
   - Command-pattern edits; full undo/redo; each committed change can create a Plan version
     (Phase 03) — autosave with version checkpoints.

6. **Selection & inspector**
   - Click/marquee select; multi-select; the right inspector edits properties of the selection
     (room type/area, wall thickness, opening size). Keyboard nudging.

---

## Deliverables

- A 2D editor that opens a generated `Plan` and supports wall/room/opening/dimension editing with
  snapping, undo/redo, and live validation overlay.
- Edits persist as new Plan versions via the API.

## Acceptance criteria

- Dragging a shared wall moves both adjacent rooms and updates their areas live and correctly.
- Placing a door on a wall hosts it; moving the wall moves the door; deleting the wall warns.
- A numeric area edit on a room resizes it to within ±1% of target while staying valid geometry.
- Editing an undersized room above the minimum clears its code flag in the overlay within a second.
- Undo/redo restores exact prior geometry; reload shows the last autosaved version.

## Sources

- react-konva: https://konvajs.org/docs/react/
- Constraint/snapping concepts (CAD): https://en.wikipedia.org/wiki/Geometric_constraint_solving
- Command pattern for undo: https://refactoring.guru/design-patterns/command
- shapely (edit-time geometry ops in the browser via geometry-core / or server round-trip)

---

## Claude build prompt

> Implement Phase 10 (2D Plan Editor) per `plan/phase-10-2d-plan-editor.md` on the Phase-04 Konva
> stage. Render the active level with room fills colored by type (+legend), true-thickness walls
> with correct joins, door/window symbols with swing arcs, stairs, fixtures, and a dimension layer,
> with layer toggles, pan/zoom, rulers, and print-accurate scale. Implement editing tools: wall
> (draw/split/join/drag with attached rooms reflowing, thickness/type), room (reshape/split/merge,
> set type/label, numeric area resize that solves an edge move), opening (place/move doors+windows
> hosted to walls with offset snapping and width/height/swing), and dimensions (linear/aligned/
> angular + auto-dimension). Build a snapping/constraints engine (grid, endpoint, midpoint,
> perpendicular, parallel, extension, ortho lock, numeric override) that keeps walls connected and
> preserves Phase-02 geometry invariants on every edit. Add a debounced live-validation overlay that
> calls the Phase-09 validate service and shows inline code flags with citation+fix-hint on hover
> plus a click-to-zoom issues panel. Implement command-pattern undo/redo with autosave that commits
> Plan versions via the Phase-03 API, plus selection/marquee and an inspector for the selection.
> Acceptance: dragging a shared wall updates both rooms' areas live, openings stay hosted to their
> walls, a numeric area edit lands within ±1% while staying valid, fixing an undersized room clears
> its flag within a second, and undo/redo restores exact prior geometry.
