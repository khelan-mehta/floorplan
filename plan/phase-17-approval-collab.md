# Phase 17 — Approval & Collaboration Workflow

**Goal:** Support the brief's business process: options go to the **client for approval**, the
selected one **moves forward**. Add sharing, client review (with comments/markup), approval state,
and version control so the chosen plan continues into Revit/documentation.

**Depends on:** Phases 03 (auth/versions), 11, 14, 15.

---

## Tasks

1. **Sharing & client access**
   - Share a project or a curated **variant set** (Phase 14) with a client via a `client` role or a
     tokenized read/comment link (no account needed). Scope: view 2D/3D, comment, approve — not edit.
   - A clean **client review view**: gallery of options, 3D walkthrough, key metrics, no internal UI.

2. **Comments & markup**
   - Threaded comments anchored to a plan, a room, or a 3D point (pin annotations). Mentions,
     resolve/reopen, and a per-variant comment feed. Optional redline/markup on the 2D plan.

3. **Approval state machine**
   - Per variant: `draft → shared → in_review → changes_requested → approved → archived`. Record who
     approved, when, and on which Plan **version** (immutable snapshot). Only one variant can be the
     project's `approved` option; approving locks that version for downstream export/Revit.

4. **Notifications**
   - Email/in-app notifications on share, new comment, approval, or change request. Digest options.

5. **Version control UX**
   - Timeline of Plan versions with thumbnails, restore/branch, compare any two versions (reuse
     Phase 14 compare + Phase 03 diff). Tag versions ("sent to client v2", "approved").

6. **Approval → handoff**
   - On approval, auto-generate the deliverable package (DWG + IFC + PDF sheets + schedules from
     Phase 15) and make it downloadable / pushable to Revit (Phase 16). Stamp with approval metadata.

7. **Audit log**
   - Immutable log of shares, comments, approvals, exports for accountability.

---

## Deliverables

- Client sharing (role + tokenized link) and a focused client review view.
- Anchored threaded comments/markup; approval state machine tied to immutable versions.
- Notifications, version timeline with compare/restore, and an approval→deliverable-package handoff.
- Audit log.

## Acceptance criteria

- A client opens a share link, browses options in 3D, comments on a room, and approves one — without
  an account or edit access.
- Approval pins a specific immutable Plan version and generates the DWG/IFC/PDF package automatically.
- Requesting changes moves state correctly and notifies the team; the timeline shows the history.
- Only one approved option exists per project; the audit log records the chain of events.

## Sources

- State machines: https://xstate.js.org/ (or a server-side enum FSM)
- Anchored comments pattern (e.g. Figma-style): conceptual
- Tokenized share links / capability URLs: https://www.w3.org/TR/capability-urls/
- (Reuses Phase 03 versioning/diff, Phase 14 compare, Phase 15 export.)

---

## Claude build prompt

> Implement Phase 17 (Approval & Collaboration Workflow) per `plan/phase-17-approval-collab.md`. Add
> project/variant-set sharing via the `client` role and tokenized read/comment links (no account
> required) plus a focused client review view (option gallery, 3D walkthrough, key metrics, no
> internal UI). Build threaded comments anchored to a plan/room/3D-pin with mentions and
> resolve/reopen, plus optional 2D redline markup. Implement a per-variant approval state machine
> (draft→shared→in_review→changes_requested→approved→archived) recording approver/time/immutable
> Plan version, enforcing a single approved option per project and locking that version. Add email/
> in-app notifications on share/comment/approval/change-request, a version timeline with thumbnails,
> compare (reusing Phase 14) and restore/branch (reusing Phase 03 diff), and version tagging. On
> approval, auto-generate the Phase-15 deliverable package (DWG+IFC+PDF+schedules) stamped with
> approval metadata and ready for Phase-16 Revit handoff. Add an immutable audit log of shares,
> comments, approvals, and exports. Acceptance: a client opens a share link, browses options in 3D,
> comments on a room, and approves one with no account or edit rights; approval pins an immutable
> version and auto-builds the deliverable package; change-requests transition state and notify the
> team; exactly one approved option exists per project; and the audit log captures the full chain.
