# Generative 3D Floor Plan Studio — Implementation Plan

A web-based tool that **generates code-compliant 3D floor plans** inside a user-supplied
building outline, driven by an **area-programming spreadsheet (Excel)** and a **room adjacency
graph**, constrained by **local building codes** (ingested via RAG), lets users **edit/swap rooms
and interiors** in the browser, and **exports to DWG/IFC** so architects can continue the work in
**Autodesk Revit**.

This folder is the **build playbook**. Each `phase-XX-*.md` file is a self-contained unit of work
you can paste to Claude as a build prompt. Phases are ordered so each builds on the previous,
but most can be developed in parallel by separate agents once the contracts in Phases 1–4 exist.

---

## How to use this plan

1. Read `00-architecture-and-stack.md` first — it defines the system, the data contracts, the
   tech stack, and the repository layout that every later phase assumes.
2. Build phase-by-phase. Each phase file ends with a **"Claude build prompt"** block — copy it
   verbatim into a fresh Claude Code session inside this repo to implement that phase.
3. Each phase declares **Depends on** (what must exist first) and **Deliverables / Acceptance
   criteria** (how you know it is done). Do not start a phase until its dependencies pass their
   acceptance criteria.
4. Treat the **data schemas** in Phase 2 as the single source of truth. If a later phase needs a
   schema change, update Phase 2 first, then regenerate the typed clients.

---

## The product in one diagram

```
            ┌──────────────────────────────────────────────────────────────────┐
            │                         WEB APP (browser)                         │
            │ Boundary editor → Area-program (Excel) + graph → Generate → 2D/3D  │
            │        React + React-Three-Fiber (3D) + 2D canvas + Zustand        │
            └───────────────┬───────────────────────────────────┬──────────────┘
                            │ REST/WebSocket (typed)              │ glTF / Fragments
                            ▼                                     ▼
            ┌──────────────────────────────┐        ┌───────────────────────────┐
            │      API GATEWAY (FastAPI)    │        │  ASSET/GEOMETRY SERVICES  │
            │  auth, projects, versions,    │        │  3D solidify (walls,      │
            │  orchestration, job queue     │        │  floors, openings), glTF  │
            └───┬─────────────┬─────────────┘        └───────────────────────────┘
                │             │
                ▼             ▼
   ┌────────────────────┐  ┌───────────────────────────────────────────────┐
   │ GENERATIVE ENGINE  │  │            BUILDING-CODE RAG SERVICE           │
   │ graph+boundary →   │  │  ingest codes → chunk → embed → vector DB →    │
   │ room layout        │◄─┤  retrieve → extract machine-checkable rules    │
   │ (ML + solver)      │  │  (setbacks, min areas, egress, stairs, MEP)    │
   └─────────┬──────────┘  └───────────────────────────────────────────────┘
             ▼
   ┌────────────────────┐         ┌───────────────────────────────────────┐
   │  CODE VALIDATOR     │         │            EXPORT SERVICE             │
   │  scores + flags     │         │  Plan → DXF/DWG (ODA) + IFC (Revit)   │
   └────────────────────┘         └───────────────────────────────────────┘
```

---

## Phase index

| # | Phase | What you get |
|---|-------|--------------|
| 00 | [Architecture & stack](00-architecture-and-stack.md) | System design, data contracts, repo layout, tech decisions |
| 01 | [Foundations & tooling](phase-01-foundations.md) | Monorepo, CI, linting, env, docker-compose dev stack |
| 02 | [Domain model & schemas](phase-02-domain-model.md) | Canonical JSON schemas: boundary, program graph, plan, codes |
| 03 | [Backend core & persistence](phase-03-backend-core.md) | FastAPI, Postgres, auth, projects, versions, job queue |
| 04 | [Frontend shell](phase-04-frontend-shell.md) | React app, routing, state, design system, typed API client |
| 05 | [Boundary input](phase-05-boundary-input.md) | Draw/import the floor outline; site setbacks; levels |
| 06 | [Program input (Excel + graph)](phase-06-room-graph-input.md) | Area-program spreadsheet import/export + node-edge adjacency editor |
| 07 | [Building-code RAG](phase-07-buildingcode-rag.md) | Ingest codes, retrieve, extract machine-checkable rules |
| 08 | [Generative layout engine](phase-08-generative-engine.md) | Graph + boundary → room layouts (ML + procedural solver) |
| 09 | [Code constraints & scoring](phase-09-code-constraints.md) | Apply/validate code rules; score and flag violations |
| 10 | [2D plan editor](phase-10-2d-plan-editor.md) | Render and edit walls, rooms, doors, dimensions |
| 11 | [3D model generation](phase-11-3d-model.md) | Solidify plan → 3D walls/floors/openings/roof, glTF |
| 12 | [Component & interior library](phase-12-component-library.md) | Parametric furniture/fixtures catalog + placement rules |
| 13 | [Interactive editing](phase-13-interactive-editing.md) | Swap room types, move walls, place/swap interiors |
| 14 | [Variants & comparison](phase-14-variants-workflow.md) | Generate N options, score, compare side-by-side |
| 15 | [Export to DWG/IFC](phase-15-export-dwg-ifc.md) | DXF→DWG (ODA) + IFC4 export with layers/storeys |
| 16 | [Revit interoperability](phase-16-revit-integration.md) | IFC roundtrip + optional Revit/Dynamo add-in |
| 17 | [Approval & collaboration](phase-17-approval-collab.md) | Sharing, comments, client approval, versioning |
| 18 | [Deploy, scale, observe](phase-18-deploy-scale.md) | Infra, queues, GPU workers, monitoring, cost controls |
| 19 | [Testing & QA](phase-19-testing-qa.md) | Unit/integration/e2e/geometry/golden-file testing |
| 20 | [Hardening & polish](phase-20-hardening-polish.md) | Security, performance, accessibility, docs, onboarding |

---

## Guiding principles

- **Geometry is data, not pixels.** Everything is stored as a vector model (Phase 2). 2D, 3D,
  DWG, and IFC are all *renderers/exporters* of the same model. Never let a view own the truth.
- **The generator proposes; the validator disposes.** Generation and code-compliance are
  separate services. A plan is only "valid" when the validator says so, with line-item reasons.
- **Codes are retrieved, not hard-coded.** Building codes differ by jurisdiction. The RAG service
  turns prose code into machine-checkable rule objects so the same engine serves any locale.
- **Everything round-trips to Revit.** IFC4 is the primary BIM interchange; DWG is the 2D
  drawing deliverable. Validate exports against Revit early and often (Phase 16).
- **Human-in-the-loop.** The tool accelerates an architect; it does not replace approval. Every
  generated artifact is editable and every edit is versioned for the client-approval workflow.

---

## Key external references (used across phases)

- Graph2Plan — layout graph + boundary → floorplan: https://arxiv.org/abs/2004.13204
- House-GAN / House-GAN++ — graph-constrained layout GAN: https://arxiv.org/pdf/2003.06988
- HouseDiffusion — vector floorplan via diffusion: https://arxiv.org/abs/2211.13287
- RPLAN dataset (training data for layouts): http://staff.ustc.edu.cn/~fuxm/projects/DeepLayout/index.html
- ezdxf (DXF read/write) + ODA File Converter add-on (DWG): https://ezdxf.readthedocs.io/
- That Open / web-ifc (IFC read/write in JS/WASM): https://github.com/ThatOpen/engine_web-ifc
- React Three Fiber (3D in React): https://r3f.docs.pmnd.rs/
- IFC4 schema (buildingSMART): https://standards.buildingsmart.org/IFC/RELEASE/IFC4/

> Per-phase reference lists appear inside each phase file under **Sources**.
