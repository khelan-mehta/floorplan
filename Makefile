# Convenience wrapper for Unix users. On Windows (no make), use the equivalent
# `corepack pnpm <script>` commands shown in README / package.json.
.DEFAULT_GOAL := help

.PHONY: help dev dev-web install lint typecheck test format codegen

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install JS deps
	pnpm install

dev: ## Bring up the full dockerized dev stack
	docker compose -f infra/docker-compose.yml up

dev-web: ## Run just the web app (Vite)
	pnpm --filter @fpg/web dev

lint: ## Lint (eslint + prettier check)
	pnpm lint

typecheck: ## Typecheck all JS packages
	pnpm typecheck

test: ## Run all tests
	pnpm test

format: ## Format with prettier
	pnpm format

codegen: ## Regenerate types from schemas (wired in Phase 02)
	pnpm codegen
