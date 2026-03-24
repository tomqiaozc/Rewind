.PHONY: help dev up down migrate test lint typecheck backend-dev web-dev install docker-build-backend docker-build-web docker-build

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure ──────────────────────────────────────────────

up: ## Start local dev services (PostgreSQL + Azurite)
	docker compose up -d

down: ## Stop local dev services
	docker compose down

# ── Install ─────────────────────────────────────────────────────

install: ## Install all dependencies
	cd backend && pip install -e ".[dev]"
	cd cli && pip install -e ".[dev]"
	cd packages/web && npm install

# ── Backend ─────────────────────────────────────────────────────

backend-dev: ## Start FastAPI dev server
	cd backend && uvicorn src.main:app --reload --port 8000

migrate: ## Run Alembic migrations
	cd backend && alembic upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new MSG="description")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

backend-test: ## Run backend tests
	cd backend && pytest -v --tb=short

backend-lint: ## Lint backend code
	cd backend && ruff check src/ tests/

backend-format: ## Format backend code
	cd backend && ruff format src/ tests/

backend-typecheck: ## Type-check backend code
	cd backend && mypy src/

# ── CLI ─────────────────────────────────────────────────────────

cli-test: ## Run CLI tests
	cd cli && pytest -v --tb=short

cli-lint: ## Lint CLI code
	cd cli && ruff check src/ tests/

# ── Frontend ────────────────────────────────────────────────────

web-dev: ## Start Next.js dev server
	cd packages/web && npm run dev

web-build: ## Build Next.js for production
	cd packages/web && npm run build

web-lint: ## Lint frontend code
	cd packages/web && npm run lint

web-typecheck: ## Type-check frontend code
	cd packages/web && npx tsc --noEmit

# ── Docker ──────────────────────────────────────────────────────

docker-build-backend: ## Build backend Docker image
	docker build -t rewind-backend:latest backend/

docker-build-web: ## Build frontend Docker image
	docker build -t rewind-web:latest packages/web/

docker-build: docker-build-backend docker-build-web ## Build all Docker images

# ── Combined ────────────────────────────────────────────────────

test: backend-test cli-test ## Run all tests

lint: backend-lint cli-lint web-lint ## Lint all code

typecheck: backend-typecheck web-typecheck ## Type-check all code

dev: up backend-dev ## Start everything for development
