# Rewind

AI coding session intelligence platform. Ingest, index, search, and replay conversations from AI coding assistants.

**Live:** [app-frontend-rwnd-prod.azurewebsites.net](https://app-frontend-rwnd-prod.azurewebsites.net)

## What it does

Rewind captures your AI coding assistant conversations (Claude Code, OpenCode, Gemini CLI), syncs them to the cloud, and provides a web dashboard for searching, replaying, and organizing sessions.

- **Sync** — CLI discovers local AI tool sessions, parses them, uploads to cloud
- **Search** — Full-text search across all session content and tool invocations
- **Replay** — Message-by-message session replay with code highlighting
- **Organize** — Star, tag, trash, and filter sessions by source/project

## Production Environment

| Resource | Value |
|----------|-------|
| Frontend | [app-frontend-rwnd-prod.azurewebsites.net](https://app-frontend-rwnd-prod.azurewebsites.net) |
| Backend API | [app-backend-rwnd-prod.azurewebsites.net](https://app-backend-rwnd-prod.azurewebsites.net) |
| Region | Azure East Asia |
| Database | PostgreSQL Flexible Server (`pg-rwnd-prod`) |
| Blob Storage | Azure Storage Account (`strwndprod`) |
| Key Vault | `kv-rwnd-prod` |
| Resource Group | `rg-rewind-ea` |
| Container Images | `ghcr.io/tomqiaozc/rewind/backend`, `ghcr.io/tomqiaozc/rewind/frontend` |
| CI/CD | GitHub Actions → GHCR → Azure App Service |

## Architecture

```
Browser → Next.js (NextAuth) → BFF Proxy → FastAPI → PostgreSQL / Azure Blob
CLI → FastAPI API (Bearer rw_... key) → PostgreSQL / Azure Blob
```

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.9+, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Pydantic v2 |
| Frontend | Next.js 16, React 19, Tailwind CSS v4, shadcn/ui, Recharts |
| CLI | Python, Typer, httpx, Rich |
| Database | PostgreSQL 16 (FTS via tsvector) |
| Storage | Azure Blob Storage |
| Auth | NextAuth v5 (Google OAuth) + API keys for CLI |
| Infra | Azure App Service, Bicep IaC, GitHub Actions CI/CD |

## Getting Started (Production)

### 1. Sign in to the dashboard

Open [app-frontend-rwnd-prod.azurewebsites.net](https://app-frontend-rwnd-prod.azurewebsites.net) and sign in with Google.

### 2. Create an API key

Go to **Settings > API Keys**, enter a device name, and click **Create Key**. Copy the `rw_...` key immediately — it's shown only once.

### 3. Install the CLI

```bash
cd cli
pip install -e .
```

If `rewind` is not found after install, add the Python scripts directory to your PATH:

```bash
# macOS (Python 3.9)
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 4. Log in and sync

```bash
rewind login --api-url https://app-backend-rwnd-prod.azurewebsites.net
# Paste your API key when prompted

rewind sync           # Upload all AI sessions
rewind status         # Check sync state
```

## Local Development

### Prerequisites

- Python 3.9+
- Node.js 20+
- Docker & Docker Compose

### Setup

```bash
git clone https://github.com/tomqiaozc/Rewind.git && cd Rewind
make install          # Install all deps (backend + CLI + frontend)
make up               # Start PostgreSQL + Azurite containers
cp .env.example .env  # Defaults work for local dev
make migrate          # Run database migrations
```

### Create a dev user and API key

```bash
docker exec -i rewind-postgres-1 psql -U rewind -d rewind <<'SQL'
INSERT INTO users (id, email, name)
VALUES ('00000000-0000-0000-0000-000000000001', 'dev@localhost', 'Dev User')
ON CONFLICT (email) DO NOTHING;

INSERT INTO api_keys (id, user_id, key_hash, device_name)
VALUES (
  '00000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000001',
  encode(sha256('rw_dev_local_key_1234567890abcdef1234567890abcdef'::bytea), 'hex'),
  'local-dev'
) ON CONFLICT (key_hash) DO NOTHING;
SQL
```

### Start services

```bash
make backend-dev      # FastAPI on http://localhost:8000
make web-dev          # Next.js on http://localhost:3000 (separate terminal)
```

For the frontend, create `packages/web/.env.local`:

```
NEXT_PUBLIC_API_KEY=rw_dev_local_key_1234567890abcdef1234567890abcdef
```

### Use the CLI locally

```bash
cd cli && pip install -e .
rewind login          # Use default http://localhost:8000
rewind sync --dry-run # Preview what would be synced
rewind sync           # Sync AI sessions
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies |
| `make up` / `make down` | Start / stop Docker containers |
| `make migrate` | Run database migrations |
| `make backend-dev` | FastAPI dev server (port 8000) |
| `make web-dev` | Next.js dev server (port 3000) |
| `make test` | Run all tests (backend + CLI) |
| `make lint` | Lint all code (Ruff + ESLint) |
| `make typecheck` | Type-check all code (mypy + tsc) |

## Supported AI Tools

| Tool | Format | Status |
|------|--------|--------|
| Claude Code | JSONL (`~/.claude/projects/**/*.jsonl`) | Supported |
| OpenCode | SQLite + JSON (`~/.local/share/opencode/`) | Supported |
| Gemini CLI | JSON (`~/.gemini/tmp/**/chats/session-*.json`) | Supported |

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/user-guide.md) | End-to-end feature walkthrough |
| [Deployment Manual](docs/deployment-manual.md) | Production deployment guide |
| [Production Runbook](docs/runbook.md) | Operations and incident response |
| [Architecture Blueprint](docs/blueprint/03-architecture-blueprint.md) | Technical architecture |

## License

MIT
