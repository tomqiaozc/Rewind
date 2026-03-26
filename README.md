# Rewind

AI coding session intelligence platform. Ingest, index, search, and replay conversations from AI coding assistants.

## What it does

Rewind captures your AI coding assistant conversations (Claude Code, OpenCode, Gemini CLI), syncs them to the cloud, and provides a web dashboard for searching, replaying, and organizing sessions.

**Core workflows:**
- **Sync** — CLI discovers local AI tool sessions, parses them, uploads to cloud
- **Search** — Full-text search across all session content and tool invocations
- **Replay** — Message-by-message session replay with code highlighting
- **Organize** — Star, tag, trash, and filter sessions by source/project

## Architecture

```
Browser → Next.js (NextAuth) → BFF Proxy → FastAPI → PostgreSQL / Azure Blob
CLI → FastAPI API (Bearer rw_... key) → PostgreSQL / Azure Blob
```

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Pydantic v2 |
| Frontend | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui, Recharts |
| CLI | Python, Typer, httpx, Rich |
| Database | PostgreSQL 16 (FTS via tsvector) |
| Storage | Azure Blob Storage |
| Auth | NextAuth v5 (Google OAuth) + API keys for CLI |
| Infra | Azure App Service, Bicep IaC, GitHub Actions CI/CD |

## Project Structure

```
├── backend/           # Python FastAPI API server
│   ├── src/
│   │   ├── api/       # API route handlers
│   │   ├── auth/      # Dual auth (API key + BFF proxy)
│   │   ├── core/      # Shared types, constants, validators
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic request/response schemas
│   │   ├── services/  # Business logic
│   │   └── middleware/ # Rate limiting, logging, security headers
│   ├── alembic/       # Database migrations
│   └── tests/
├── packages/web/      # Next.js frontend
│   └── src/
│       ├── app/       # App Router pages
│       ├── components/ # React components + shadcn/ui
│       └── lib/       # API client, types, utilities
├── cli/               # Python CLI for syncing sessions
│   └── src/
│       ├── commands/  # login, sync, status
│       ├── parsers/   # Claude, OpenCode, Gemini parsers
│       ├── drivers/   # File and DB incremental readers
│       └── upload/    # Upload engine
├── infra/             # Azure Bicep templates
│   ├── main.bicep
│   ├── modules/       # App Service, PostgreSQL, Storage, Key Vault, Monitoring
│   └── parameters/    # dev.bicepparam, prod.bicepparam
├── docs/
│   ├── blueprint/     # Architecture and implementation blueprint
│   └── deployment-manual.md  # Production deployment guide
└── .github/workflows/ # CI and deploy pipelines
```

## Quick Start (Local Development)

### Prerequisites

- Python 3.9+
- Node.js 20+
- Docker & Docker Compose

### 1. Clone and install dependencies

```bash
git clone <repo-url> && cd Rewind
make install
```

### 2. Start local services (PostgreSQL + Azurite)

```bash
make up
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local dev)
```

### 4. Run database migrations

```bash
make migrate
```

### 5. Start the backend

```bash
make backend-dev
# API available at http://localhost:8000
# Health check: http://localhost:8000/api/health
```

### 6. Start the frontend (in a separate terminal)

```bash
make web-dev
# Dashboard at http://localhost:3000
```

### 7. Install and use the CLI

```bash
cd cli && pip install -e .
rewind login          # Configure API URL and key
rewind sync --dry-run # Preview what would be synced
rewind sync           # Sync AI sessions to the backend
rewind status         # Check auth and tracked files
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make up` | Start PostgreSQL + Azurite containers |
| `make down` | Stop containers |
| `make install` | Install all dependencies |
| `make migrate` | Run database migrations |
| `make backend-dev` | Start FastAPI dev server (port 8000) |
| `make web-dev` | Start Next.js dev server (port 3000) |
| `make test` | Run all backend + CLI tests |
| `make lint` | Lint all code (Ruff + ESLint) |
| `make typecheck` | Type-check all code (mypy + tsc) |
| `make docker-build` | Build Docker images for backend + frontend |

## CLI Commands

| Command | Description |
|---------|-------------|
| `rewind login` | Configure API URL and API key |
| `rewind sync` | Discover and upload AI sessions |
| `rewind sync --source claude` | Sync only Claude Code sessions |
| `rewind sync --dry-run` | Preview without uploading |
| `rewind status` | Show auth status and tracked files |
| `rewind --version` | Show CLI version |

## Supported AI Tools

| Tool | Format | Status |
|------|--------|--------|
| Claude Code | JSONL (`~/.claude/projects/**/*.jsonl`) | Implemented |
| OpenCode | SQLite + JSON fallback (`~/.local/share/opencode/`) | Implemented |
| Gemini CLI | JSON (`~/.gemini/tmp/**/chats/session-*.json`) | Implemented |
| Codex CLI | JSONL | Planned |
| VSCode Copilot | CRDT JSONL | Planned |

## Testing

```bash
# All tests
make test

# Backend only
cd backend && pytest

# CLI only
cd cli && pytest

# With verbose output
cd backend && pytest -v
```

## Deployment

See [docs/deployment-manual.md](docs/deployment-manual.md) for the complete production deployment guide covering:
- Azure infrastructure provisioning (Bicep)
- Google OAuth setup
- Secret management (Key Vault)
- CI/CD pipeline (GitHub Actions)
- Custom domain & TLS
- Monitoring & alerting

## Documentation

| Document | Description |
|----------|-------------|
| [Deployment Manual](docs/deployment-manual.md) | Step-by-step production deployment |
| [Production Runbook](docs/runbook.md) | Operations and incident response |
| [Blueprint Index](docs/blueprint/00-index.md) | Architecture and design decisions |
| [Architecture Blueprint](docs/blueprint/03-architecture-blueprint.md) | Detailed technical architecture |
| [Implementation Plan](docs/blueprint/04-azure-and-implementation.md) | Phased build plan |

## License

MIT
