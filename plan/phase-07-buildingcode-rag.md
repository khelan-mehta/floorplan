# Phase 07 — Building-Code Ingestion & RAG

**Goal:** Turn jurisdiction building codes (PDF/HTML prose) into a searchable knowledge base AND a
set of **machine-checkable `Rule` objects** the validator (Phase 09) and generator (Phase 08) can
consume. This is the "building code available online, documented and RAG'd" requirement.

**Depends on:** Phases 02–03. Feeds Phases 08, 09, 06.

> Two outputs from one pipeline: (a) a **retrieval index** for human Q&A and citations, and
> (b) a **structured RuleSet** of executable constraints. Both trace back to source sections.

---

## Tasks

1. **Code ingestion pipeline (`services/codes`)**
   - Source registry: per jurisdiction, a list of documents (IBC, IRC, local amendments, NBC,
     Eurocodes, etc.) with URLs/files, version, effective date, and license/usage notes.
   - Parse PDFs/HTML with `pymupdf`/`unstructured`: preserve section numbers, tables, headings.
   - **Chunk** by section/clause (not fixed token windows) so a chunk = a self-contained rule with
     its citation. Keep tables intact (many codes are tabular: min areas, widths, occupancy loads).

2. **Embedding + vector store**
   - Embed chunks; store in **Qdrant** (or pgvector) with metadata: jurisdiction, doc, section,
     version, room_types affected, category. Hybrid search (dense + BM25/keyword) for clause
     numbers and exact terms.

3. **Retrieval API**
   - `GET /codes?jurisdiction=` → available rule sets.
   - `POST /codes/query` → semantic search returning chunks + citations (powers an in-app
     "ask the code" assistant and inspector tooltips).

4. **Rule extraction (prose → structured `Rule`)**
   - For each relevant clause, use the **Claude API** with a strict tool/JSON schema to extract
     `Rule` objects (Phase 02): category, applies_to, predicate (the small DSL from Phase 09),
     severity, and a verbatim citation. Use prompt caching for the large code context.
   - Human-in-the-loop review UI: extracted rules listed with their source text side-by-side;
     a reviewer approves/edits before a RuleSet is marked `published`. **Never auto-trust
     extraction for compliance** — flag low-confidence extractions.
   - Categories to target first (highest value, most checkable): minimum room areas & dimensions,
     minimum ceiling heights, door/corridor widths, **egress** (travel distance, number/width of
     exits), window-to-floor-area (daylight/ventilation), stair geometry (rise/run/landings),
     accessibility clearances, setbacks/FAR/coverage, occupancy-based requirements.

5. **Rule DSL & registry**
   - Define the predicate DSL once (shared with Phase 09): e.g.
     `room.type in [bedroom] ⇒ room.area_mm2 >= 7_000_000` ; `door.width_mm >= 815` ;
     `egress.travel_distance_mm <= 45_000`. Parameters can be tabular/occupancy-dependent.
   - Version + diff rule sets so a code update produces a reviewable changelog.

6. **Jurisdiction management**
   - Admin UI to add a jurisdiction, upload docs, run ingestion, review extracted rules, publish.
   - A small seed set: ship 1–2 fully worked example jurisdictions (e.g. a generic IBC-like set and
     one local set) so downstream phases have real rules to test against.

---

## Deliverables

- Ingestion → index → extracted, human-reviewed `RuleSet` for ≥1 jurisdiction.
- `POST /codes/query` semantic search with citations.
- Admin review UI for extracted rules; published RuleSets readable by `GET /rulesets/{id}`.

## Acceptance criteria

- Asking "minimum bedroom area?" returns the correct clause + citation for the seeded jurisdiction.
- The seeded RuleSet contains executable predicates for ≥10 categories, each with a citation.
- Re-ingesting an updated document produces a rule diff for review, not a silent overwrite.
- Low-confidence extractions are flagged and excluded from `published` until approved.

## Sources

- RAG overview: https://www.databricks.com/glossary/retrieval-augmented-generation-rag
- Qdrant: https://qdrant.tech/  · pgvector: https://github.com/pgvector/pgvector
- Claude API tool use / structured output: https://docs.anthropic.com/en/docs/build-with-claude/tool-use
- Prompt caching: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- PyMuPDF: https://pymupdf.readthedocs.io/  · unstructured: https://docs.unstructured.io/
- IBC reference (example): https://codes.iccsafe.org/

> ⚠️ **Compliance disclaimer:** extracted rules are a decision-support aid, not a legal compliance
> guarantee. Surface citations everywhere; require a licensed professional's sign-off. Bake this
> disclaimer into the UI and exports.

---

## Claude build prompt

> Implement Phase 07 (Building-Code Ingestion & RAG) per `plan/phase-07-buildingcode-rag.md` in
> `services/codes`. Build an ingestion pipeline with a per-jurisdiction document registry (URL,
> version, effective date, license), PDF/HTML parsing via PyMuPDF/unstructured that preserves
> section numbers and tables, and clause-level chunking where each chunk is a self-contained rule
> with its citation. Embed chunks into Qdrant (or pgvector) with metadata (jurisdiction, doc,
> section, version, affected room types, category) and hybrid dense+keyword search. Expose
> `GET /codes?jurisdiction=` and `POST /codes/query` returning chunks with citations. Implement
> rule extraction that uses the Claude API with a strict JSON/tool schema and prompt caching to turn
> clauses into Phase 02 Rule objects (category, applies_to, predicate in the shared DSL, severity,
> verbatim citation), targeting min areas/dimensions, ceiling heights, door/corridor widths, egress,
> window-to-floor ratio, stair geometry, accessibility, and setbacks/FAR. Build a human-in-the-loop
> review UI showing each extracted rule beside its source text with approve/edit and a confidence
> flag; only reviewed rules become a `published` RuleSet. Add jurisdiction admin (upload, ingest,
> review, publish), rule-set versioning with diffs on re-ingest, and ship one fully worked seed
> jurisdiction. Add a compliance disclaimer throughout. Acceptance: "minimum bedroom area?" returns
> the correct cited clause, the seed RuleSet has executable predicates for ≥10 categories, and
> re-ingesting an updated doc yields a reviewable rule diff rather than a silent overwrite.
