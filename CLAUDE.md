# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Rewind is an AI coding session intelligence platform. A CLI syncs local AI assistant conversations (Claude Code, OpenCode, Gemini CLI) to a cloud backend, which indexes them for full-text search, replay, and organization via a web dashboard.

## Development Commands

```bash
make install          # Install all deps (backend + CLI + frontend)
make up               # Start PostgreSQL + Azurite containers
make migrate          # Run Alembic migrations
make backend-dev      # FastAPI dev server on :8000
make web-dev          # Next.js dev server on :3000

make test             # All tests (backend + CLI)
make lint             # All linting (Ruff + ESLint)
make typecheck        # All type checking (mypy + tsc)

# Single test targets
cd backend && pytest tests/test_sessions.py                              # One file
cd backend && pytest tests/test_sessions.py::TestListSessions::test_list_sessions_returns_all  # One test
cd cli && pytest tests/test_parser_claude.py -v                          # CLI test file

# Formatting
make backend-format   # Ruff format backend
```

## Architecture

```
Browser -> Next.js (NextAuth) -> BFF Proxy -> FastAPI -> PostgreSQL / Azure Blob
CLI -> FastAPI API (Bearer rw_... key) -> PostgreSQL / Azure Blob
```

Three components share no code but share a contract:

- **Backend** (`backend/`): FastAPI + async SQLAlchemy 2.0 + asyncpg. Python 3.9+.
- **Frontend** (`packages/web/`): Next.js 16, React 19, App Router, Tailwind CSS v4, shadcn/ui.
- **CLI** (`cli/`): Typer + httpx + Rich. Installs as `rewind` command.

### Auth (dual-path, never implement OAuth in Python)

NextAuth v5 (Google OAuth) is the sole session issuer for web users. The Python backend has two auth paths:
1. **API key**: `Authorization: Bearer rw_...` — SHA-256 hashed and matched in `api_keys` table. Used by CLI.
2. **BFF proxy**: `X-Backend-Secret` + `X-User-Id` headers set by Next.js after validating the NextAuth session.

### Ingest pipeline

CLI discovers local sessions -> parses to canonical format (`CanonicalSession`/`CanonicalMessage`) -> uploads to backend. Backend uses 4-field idempotency check (`content_hash`, `raw_hash`, `parser_revision`, `schema_version`). Content stored in Azure Blob; metadata + FTS in PostgreSQL.

### Full-text search

Messages are chunked into 2000-char `message_chunks` with a `tsvector` generated column. FTS safety: control char delimiters for `ts_headline`, then HTML-escape, then replace with `<mark>` tags.

### Backend layers

Routes (`src/api/`) -> Services (`src/services/`) -> Models (`src/models/`). Schemas in `src/schemas/`, shared types in `src/core/`. Config via pydantic-settings loading from `.env`.

### Frontend patterns

App Router pages under `src/app/dashboard/`. API client in `src/lib/api.ts` uses `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). Path alias `@/*` maps to `./src/*`. Uses `output: "standalone"` for Docker builds.

### CLI parsers

Each AI tool has a parser (`src/parsers/`) and driver (`src/drivers/`). Drivers handle incremental file/DB reading; parsers convert to canonical types. Sync cursors track what's been uploaded.

## Testing Notes

- Backend tests use in-memory SQLite (via aiosqlite) as a stand-in for PostgreSQL. Tests override FastAPI dependencies (`get_db`, `get_current_user`).
- CLI tests use pytest-asyncio.
- Frontend tests are not yet configured (Vitest planned).
- `pytest-asyncio` mode is `auto` for backend.

## Linting and Type Checking

- **Python**: Ruff (line-length 100, target py39). Rules: E, F, W, I, N, UP, B, A, SIM, TCH. Several per-file ignores for Pydantic/SQLAlchemy/FastAPI runtime annotation needs — check `pyproject.toml` before adding new ignores.
- **Python types**: mypy strict mode. Backend uses Pydantic mypy plugin.
- **Frontend**: ESLint with `eslint-config-next` (core-web-vitals + typescript).

## Database Migrations

```bash
make migrate                           # Apply all pending
make migrate-new MSG="add foo table"   # Generate new migration
```

Alembic config in `backend/alembic/`. Migration env overrides DB URL from `DATABASE_URL` env var.

## Environment

Root `.env` (copy from `.env.example`) for backend. Frontend uses `packages/web/.env.local` separately (`NEXT_PUBLIC_API_KEY` for local dev, NextAuth vars for production).

## Infrastructure

Azure-first: App Service for compute, PostgreSQL Flexible Server, Blob Storage, Key Vault, App Insights. Bicep IaC in `infra/`. CI runs tests in matrix (Python 3.9 + 3.12); deploy pushes Docker images to GHCR and deploys to Azure App Service.
