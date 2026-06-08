# Phase 04 — Frontend Shell

**Goal:** The web application skeleton: auth, routing, layout, design system, server-state wiring,
a 3D viewport scaffold, and a 2D canvas scaffold — all consuming the typed API client and Phase 02
types. No editors yet; this is the chassis the editors (Phases 5–13) mount into.

**Depends on:** Phases 02–03.

---

## Tasks

1. **App bootstrap**
   - Vite + React 18 + TS strict. Routing with **React Router**. Error boundaries + suspense.
   - Auth flow (login/register/refresh) against Phase 03; protected routes; role-aware UI gating.

2. **State & data**
   - **TanStack Query** for server cache (projects, plans, jobs) using the generated API client.
   - **Zustand** stores for editor/session state (current project, selected level, selection,
     tool mode, undo/redo stack scaffold).
   - WebSocket hook for job progress (`useJob(jobId)`), surfacing progress toasts.

3. **Design system (`packages/ui`)**
   - Tailwind + Radix primitives. Tokens for color/spacing/typography. Components: AppShell,
     Sidebar, Toolbar, Panel, Dialog, Toast, Button, Input, Select, Tabs, Tooltip, Slider,
     ContextMenu, Resizable split panes.

4. **App layout**
   - Three-region workspace: **left** = project/program tree + library, **center** = viewport
     (switchable 2D ⇆ 3D), **right** = properties/inspector. Top bar = project name, generate
     button, export menu, share. Bottom = status/validation summary.

5. **Viewport scaffolds**
   - **3D:** React-Three-Fiber `<Canvas>` with orbit controls, grid, lighting rig, a gizmo, and a
     loader that can render a glTF artifact URL (used later by Phase 11). Camera presets (top/iso).
   - **2D:** a Konva (or SVG) stage with pan/zoom, world↔screen transforms, a mm grid with
     snapping, and a ruler/dimension overlay. Both share the same camera/units utilities.

6. **Plan rendering (read-only first)**
   - Given a `Plan` from the API, render rooms (filled polygons by type color), walls (thick
     lines), openings (door/window symbols) in 2D, and the glTF in 3D. This proves the data
     contract end-to-end before any editing logic exists.

7. **Project dashboard**
   - List/create projects; open a project into the workspace; show plan thumbnails + scores.

8. **Theming, i18n scaffold, keyboard shortcut registry** (extensible; tools register hotkeys).

---

## Deliverables

- Logged-in user can create a project, land in the workspace, switch 2D/3D, and **view** a plan
  returned by the API (using a Phase 02 example fixture seeded via Phase 03).
- Job progress toasts driven by the WebSocket hook.
- Shared `packages/ui` consumed by the app.

## Acceptance criteria

- Strict TS, no `any` in app code; generated API/types are the only data shapes used.
- 2D and 3D viewports render the same example plan consistently (room colors match a legend).
- Role gating: a `viewer` sees disabled edit controls; a `client` sees only view/comment.
- Lighthouse/perf baseline captured; viewport stays interactive at 60fps for the example plan.

## Sources

- React Three Fiber: https://r3f.docs.pmnd.rs/  · drei: https://github.com/pmndrs/drei
- react-konva: https://konvajs.org/docs/react/  · TanStack Query: https://tanstack.com/query
- Zustand: https://zustand.docs.pmnd.rs/  · Radix UI: https://www.radix-ui.com/

---

## Claude build prompt

> Implement Phase 04 (Frontend Shell) per `plan/phase-04-frontend-shell.md` in `apps/web` and
> `packages/ui`. Build a Vite + React 18 + TS strict app with React Router, auth (login/register/
> refresh against the Phase 03 API), protected + role-aware routes, error boundaries, and suspense.
> Wire TanStack Query over the generated typed API client for projects/plans/jobs, Zustand stores
> for editor/session state (current project, selected level, selection, tool mode, undo/redo
> scaffold), and a `useJob` WebSocket hook surfacing progress toasts. Create a Tailwind + Radix
> design system in `packages/ui` (AppShell, Sidebar, Toolbar, Panel, Dialog, Toast, form controls,
> resizable split panes) and a three-region workspace (program/library tree | switchable 2D⇆3D
> viewport | inspector) with a top bar (generate/export/share) and a bottom validation status bar.
> Scaffold a React-Three-Fiber 3D viewport (orbit controls, grid, lighting, gizmo, glTF loader,
> camera presets) and a Konva 2D stage (pan/zoom, world↔screen transforms, mm grid with snapping,
> dimension/ruler overlay) sharing units/camera utilities. Render a read-only Plan from a seeded
> Phase 02 example fixture in BOTH 2D (rooms colored by type, walls, door/window symbols) and 3D
> (glTF), proving the data contract end-to-end. Add a project dashboard with create/open and plan
> thumbnails+scores, plus a keyboard-shortcut registry. No editing logic yet — views are read-only.
