# Rewind — AI Agent Instructions

## Project Overview

Rewind is an AI coding session intelligence platform. It consists of:

- **Backend** (`backend/`): Python FastAPI API server
- **Frontend** (`packages/web/`): Next.js 15 App Router
- **CLI** (`cli/`): Python Typer CLI for syncing sessions

## Architecture

```
Browser → Next.js (NextAuth) → BFF Proxy → FastAPI → PostgreSQL / Azure Blob
CLI → FastAPI API (Bearer rw_... key) → PostgreSQL / Azure Blob
```

## Key Constraints

1. **Auth**: NextAuth is the sole session issuer. Python backend validates API key hashes and trusts BFF proxy headers (`X-User-Id` + `X-Backend-Secret`). Never implement OAuth in Python.

2. **Ingest**: 4-field idempotency check (`content_hash`, `raw_hash`, `parser_revision`, `schema_version`). Content-Length required (411 on missing). Size limits: 50MB content, 2MB metadata, 256MB decompressed.

3. **FTS Safety**: Use control char delimiters for `ts_headline`, then HTML-escape, then replace with `<mark>` tags.

## Development Commands

```bash
make up           # Start PostgreSQL + Azurite
make migrate      # Run database migrations
make backend-dev  # Start FastAPI dev server
make web-dev      # Start Next.js dev server
make test         # Run all tests
make lint         # Lint all code
make typecheck    # Type-check all code
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), asyncpg, Pydantic v2 |
| Frontend | Next.js 15, Tailwind CSS v4, shadcn/ui, Recharts |
| CLI | Typer, httpx, Rich |
| Database | PostgreSQL 16 |
| Storage | Azure Blob Storage |
| Auth | NextAuth v5 (Google OAuth), BFF proxy pattern |

## File Organization

- Backend models: `backend/src/models/`
- Backend API routes: `backend/src/api/`
- Backend services: `backend/src/services/`
- Core types (shared): `backend/src/core/`
- Frontend pages: `packages/web/src/app/`
- Frontend components: `packages/web/src/components/`
- CLI commands: `cli/src/commands/`
- CLI parsers: `cli/src/parsers/`

## Testing

- Backend: `cd backend && pytest`
- CLI: `cd cli && pytest`
- Frontend: `cd packages/web && npm test` (Vitest, Phase 3+)
