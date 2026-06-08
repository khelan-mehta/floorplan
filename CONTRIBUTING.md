# Contributing

## Workflow

1. Branch off `main` (`feat/…`, `fix/…`, `chore/…`). Don't commit to `main` directly.
2. Keep commits small and focused; write imperative subject lines.
3. Never commit secrets. Use `.env` (copy from `.env.example`); it is gitignored.
4. Open a PR; CI (lint, typecheck, tests, codegen-drift, docker builds) must pass.

## Building by phase

This project is built phase-by-phase from [`plan/`](plan/README.md). Each `plan/phase-NN-*.md`
ends with a paste-ready **Claude build prompt**. Don't start a phase until its **Depends on** phases
meet their **Acceptance criteria**. Update [`plan/PROGRESS.md`](plan/PROGRESS.md) at each phase
boundary (status, deviations, follow-ups).

## Code standards

- **TypeScript**: strict mode, no `any` in app code. Consume only generated schema types and the
  generated API client (from Phase 02/03).
- **Python**: Ruff (lint + format) and mypy strict. FastAPI routers stay thin; put logic in pure,
  testable modules. `validator`, `geometry`, and `export` must be deterministic (no network, no
  randomness).
- **Schemas are the source of truth** (`packages/schemas`). Change a schema → run `pnpm codegen`
  (wired in Phase 02) → commit the regenerated types. CI fails on codegen drift.

## Local checks before pushing

```bash
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
```

For Python services (if working natively, needs Python 3.12 + uv):

```bash
cd apps/api        # or services/<name>
uv venv && uv pip install -e ".[dev]"
uv run ruff check . && uv run mypy app && uv run pytest -q
```

## Pre-commit hooks

```bash
pip install pre-commit   # or pipx
pre-commit install
```

Hooks run Ruff, Prettier, and basic hygiene checks on staged files.
