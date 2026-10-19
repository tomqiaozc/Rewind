# Rewind

AI coding session intelligence platform. Ingest, index, search, and replay conversations from AI coding assistants.

**Live:** [app-frontend-rwnd-prod.azurewebsites.net](https://app-frontend-rwnd-prod.azurewebsites.net)

## Why Rewind

AI coding assistants generate rich, context-dense conversations — debugging traces, architectural decisions, code reviews, refactoring plans. But these conversations vanish once the terminal closes. There's no way to search "that session where I fixed the auth bug last week", no way to see which projects consumed the most tokens, and no way to replay a session to understand how a decision was made.

Rewind solves this by treating AI coding sessions as first-class data:

- **Never lose a session** — Every conversation is automatically captured and stored in the cloud
- **Search everything** — Full-text search across all messages, tool invocations, and code snippets with highlighted results
- **Replay conversations** — Step through any session message by message, exactly as it happened
- **Track usage** — Dashboard with session counts, token usage, activity trends, and source breakdowns
- **Organize your work** — Star important sessions, tag them by topic, filter by project or AI tool, and trash what you don't need
- **Multi-tool support** — One unified interface for Claude Code, OpenCode, and Gemini CLI sessions
- **Quick search (Cmd+K)** — Instant search from anywhere in the dashboard

## Features

### Dashboard
Overview of all your AI coding activity: total sessions, message counts, token usage (input/output), activity chart over the last 90 days, and source breakdown by tool.

### Session Replay
Browse all synced sessions with source badges, tags, project names, model info, and token counts. Click into any session to replay the full conversation with timestamps and role indicators. Navigate messages with `j`/`k` keyboard shortcuts.

### Full-Text Search
PostgreSQL-powered search with stemming and stop words. Results show highlighted snippets with matching terms. Dedicated search page with debounced input, plus a Cmd+K quick search dialog accessible from any page.

### Projects
Automatically derived from your working directories. Each project card shows session count, message count, total tokens, duration, and which AI tools were used. Click to drill down into a project's sessions.

### Tags & Organization
Create colored tags to categorize sessions. Star sessions for quick access. Soft-delete to trash with one-click restore.

### CLI Sync
The `rewind` CLI discovers sessions from all supported AI tools, parses them into a canonical format, and uploads incrementally — only new/changed sessions are synced. Supports dry-run preview and per-source filtering.

## Supported AI Tools

| Tool | Format | Session Location |
|------|--------|-----------------|
| Claude Code | JSONL | `~/.claude/projects/**/*.jsonl` |
| OpenCode | SQLite + JSON | `~/.local/share/opencode/` |
| Gemini CLI | JSON | `~/.gemini/tmp/**/chats/session-*.json` |

## Getting Started

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
rewind sync --dry-run # Preview without uploading
rewind status         # Check sync state
```

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

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/user-guide.md) | End-to-end feature walkthrough |
| [Deployment Manual](docs/deployment-manual.md) | Production deployment guide |
| [Production Runbook](docs/runbook.md) | Operations and incident response |
| [Architecture Blueprint](docs/blueprint/03-architecture-blueprint.md) | Technical architecture |

For local development setup, see [CLAUDE.md](CLAUDE.md).

<!-- Cloud environment smoke check: this comment verifies the pull request workflow. -->

## License

MIT
