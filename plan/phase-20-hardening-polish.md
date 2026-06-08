# Phase 20 — Hardening, Security & Polish

**Goal:** Take the working system to production quality: security, performance, accessibility,
robustness, documentation, onboarding, and the legal/compliance posture appropriate for a tool that
touches building codes.

**Depends on:** All prior phases.

---

## Tasks

1. **Security**
   - AuthZ review on every endpoint (esp. tokenized client links and cross-org isolation). Input
     validation everywhere (already schema-driven). Rate limiting + abuse protection on generation/
     export. Signed, expiring URLs for artifacts. CSRF/CORS/CSP, security headers, dependency
     scanning (SCA), secret scanning, SAST. **File-upload safety** (DWG/PDF/image ingestion is an
     attack surface — sandbox parsers, size/type limits, no SSRF on code-doc URLs). Pen-test pass.

2. **Performance**
   - Frontend: code-split editors, lazy-load 3D, web workers for heavy geometry, instancing/LOD,
     virtualized lists. Backend: cache validation/geometry by plan hash, batch generation, profile
     hot paths. Large-building stress (many rooms/levels) with graceful degradation.

3. **Robustness & UX safety**
   - Autosave + crash recovery; optimistic UI with reconciliation; clear error states and retries;
     never lose a user's geometry. Job failure surfaced with actionable messages. Offline-tolerant
     editing where feasible.

4. **Accessibility & i18n**
   - WCAG 2.1 AA on non-canvas UI; keyboard paths for core flows; screen-reader labels; high-contrast
     theme. Localize UI and units; jurisdiction-aware defaults.

5. **Compliance & legal posture**
   - Prominent, non-dismissible **"not a substitute for professional code review"** disclaimer in
     app and on every export (DWG title block + IFC metadata). Citation traceability for every code
     rule (Phase 07). Data retention/privacy policy, terms, and per-jurisdiction code-licensing notes.
   - Export provenance: stamp deliverables with tool/version, ruleset version, and validation score.

6. **Documentation & onboarding**
   - User docs (guided tour, tooltips, sample projects), an in-app onboarding flow, and developer
     docs (architecture, schema reference, how to add a jurisdiction, how to add a component, how to
     retrain the generator). API reference from OpenAPI.

7. **Telemetry & feedback**
   - Privacy-respecting product analytics on key funnels (generate→edit→approve→export), in-app
     feedback, and a model-quality feedback loop (users rate generated options → training signal).

8. **Launch readiness**
   - Backups/restore drill, incident runbooks, status page, support process, billing/quotas
     (if commercial), and a beta with real architects against real boundaries + local codes.

---

## Deliverables

- Security review closed (SAST/SCA/secret-scan clean, upload sandboxing, pen-test fixes).
- Performance budgets met on large buildings; recovery/autosave proven.
- WCAG 2.1 AA on UI; localized; compliance disclaimers + provenance on all exports.
- Complete user + developer docs; onboarding; analytics + feedback loop; launch runbooks.

## Acceptance criteria

- A pen-test finds no critical/high issues open; malicious DWG/PDF uploads are safely rejected.
- The app recovers a session after a forced crash with no geometry loss.
- Every export carries the disclaimer, ruleset version, and validation score; code rules show
  citations in-app.
- Core flows are fully keyboard-navigable and pass axe with no serious violations.
- A new architect completes boundary→generate→edit→export guided by in-app docs without support.

## Sources

- OWASP ASVS / Top 10: https://owasp.org/www-project-application-security-verification-standard/
- WCAG 2.1: https://www.w3.org/TR/WCAG21/
- Web perf (Core Web Vitals): https://web.dev/vitals/
- SSRF prevention (code-doc fetching): https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

---

## Claude build prompt

> Implement Phase 20 (Hardening, Security & Polish) per `plan/phase-20-hardening-polish.md`. Run an
> authZ review across every endpoint (tokenized client links, cross-org isolation), add rate
> limiting/abuse protection on generation+export, signed expiring artifact URLs, CSRF/CORS/CSP and
> security headers, SCA/SAST/secret scanning, and harden all file-upload/URL-fetch paths
> (DWG/PDF/image parser sandboxing, size/type limits, SSRF protection on code-doc URLs). Optimize
> the frontend (code-split editors, lazy 3D, geometry web workers, instancing/LOD, virtualized
> lists) and backend (cache validation/geometry by plan hash, profile hot paths, large-building
> stress with graceful degradation). Add autosave/crash recovery, optimistic UI reconciliation, and
> actionable error/retry states so geometry is never lost. Reach WCAG 2.1 AA on non-canvas UI with
> full keyboard paths and screen-reader labels, and localize UI/units with jurisdiction-aware
> defaults. Add a non-dismissible "not a substitute for professional code review" disclaimer in-app
> and stamped on every export (DWG title block + IFC metadata), citation traceability for all code
> rules, export provenance (tool/version, ruleset version, validation score), and data-retention/
> licensing notices. Write complete user docs (guided tour, sample projects, onboarding) and
> developer docs (architecture, schema reference, add-a-jurisdiction, add-a-component, retrain-the-
> generator) plus the OpenAPI reference, and add privacy-respecting funnel analytics and a model-
> quality feedback loop. Prepare launch runbooks (backup/restore drill, incident response, status
> page, quotas). Acceptance: pen-test has no open critical/high issues and malicious uploads are
> rejected, the app recovers a crashed session with no geometry loss, every export carries the
> disclaimer+ruleset version+score with in-app citations, core flows pass axe and are keyboard-
> navigable, and a new architect completes boundary→generate→edit→export guided only by in-app docs.
