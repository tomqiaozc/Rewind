# 02 — New Project Definition & PRD Outline

## 5. New Project Definition

### Product Goal

Build a **session intelligence platform** that ingests, indexes, and visualizes AI coding assistant conversations. The system should support multi-source parsing, full-text search, session replay, and analytics — borrowing proven architecture patterns from a reference project while using a Python backend and Azure infrastructure.

> **Note**: The blueprint uses the product name **"Rewind"** throughout. CLI command: `rewind`. PyPI package: `rewind`. API key prefix: `rw_`.

### Target Users

- Individual developers who use AI coding assistants and want to recall, search, and review past conversations
- Engineering teams who want visibility into how AI assistants are being used across projects
- (`Pending Confirmation`) Enterprise organizations needing compliance and audit trails for AI-assisted development

### Core Workflows

1. **Install & Auth**: User installs CLI, authenticates via browser OAuth
2. **Sync**: CLI discovers local AI tool sessions, parses them, uploads to cloud
3. **Browse**: Dashboard shows session list with filters, sorting, pagination
4. **Replay**: Click into a session to see the full conversation with code blocks, tool calls, and timing
5. **Search**: Full-text search across all session content and tool invocations
6. **Organize**: Star, tag, and manage sessions; soft delete with recovery
7. **Analyze**: Dashboard overview with activity heatmaps, source distribution, project rankings

### Key Differentiators from Reference Project

| Aspect | Reference Project | New Project (Rewind) |
|--------|-----------------|-------------|
| Backend | TypeScript (Cloudflare Workers) | Python / FastAPI (Azure App Service) |
| Database | Cloudflare D1 (SQLite) | Azure Database for PostgreSQL (Flexible Server) |
| Object Storage | Cloudflare R2 | Azure Blob Storage |
| Web Hosting | Railway (Docker) | Azure App Service or Azure Container Apps |
| Worker/Queue | Cloudflare Workers (sync request) | Consolidated into FastAPI backend (no separate worker for V1) |
| Auth | NextAuth v5 + Google OAuth | NextAuth v5 + configurable OAuth providers |
| Search | SQLite FTS5 | PostgreSQL full-text search or Azure AI Search |
| Branding | Reference-specific branding | Rewind, new identity |
| CLI Runtime | Bun | Python (Typer) |

### V1 Scope

- CLI with support for **all 5 source parsers** (Claude Code, OpenCode, Gemini CLI, Codex CLI, VSCode Copilot)
- OAuth authentication (Google as default provider)
- Session sync with incremental cursors
- Web dashboard: session list, session replay, full-text search, basic stats
- Tagging and starring
- Azure deployment (App Service + PostgreSQL + Blob Storage)

### Later-Phase Scope

- Team/org features (shared sessions, role-based access)
- AI-powered features: session summaries, embeddings, semantic search
- Export and compliance features
- Custom OAuth providers (GitHub, Azure AD)
- Usage analytics and cost tracking dashboards
- CLI distribution as compiled binary

---

## 6. Reference Reuse Strategy

### What to Reuse as Reference

| Area | Reuse Level | Notes |
|------|------------|-------|
| Canonical data model (`CanonicalSession`, `CanonicalMessage`) | **High** — adopt as-is | Well-designed, source-agnostic, proven across 5 parsers |
| Dual storage pattern (metadata DB + object storage for content) | **High** — adopt pattern | Solves real size limits; port from D1+R2 to PostgreSQL+Blob |
| Message chunking for FTS | **High** — adopt pattern | Paragraph-aware splitting at ~2000 chars, no truncation |
| Ingest idempotency protocol (4-field version check) | **High** — adopt logic | `content_hash`, `raw_hash`, `parser_revision`, `schema_version` |
| CLI sync pipeline architecture | **High** — adopt pattern | Discover → parse → upload metadata → upload content → cursor rollback |
| Source parser logic (5 parsers) | **Medium** — port selectively | Rewrite in Python; format knowledge is directly transferable |
| Frontend page structure and routing | **High** — adopt structure | Dashboard, sessions, replay, search, projects, settings, trash |
| Frontend component patterns | **High** — adopt patterns | DataTable, bulk actions, session replay, activity heatmap, search dialog |
| API route design | **Medium** — redesign for Python | Same endpoints, different framework (FastAPI vs Next.js routes) |
| Auth model (dual auth: cookie + API key) | **High** — adopt pattern | Browser uses JWT cookie, CLI uses `rw_` bearer token |

### What to Re-Implement Cleanly

| Area | Reason |
|------|--------|
| Backend API layer | Python (FastAPI/Django) instead of Next.js API routes |
| Database schema | PostgreSQL instead of SQLite/D1; leverage PG features |
| Full-text search | PostgreSQL `tsvector`/`tsquery` or Azure AI Search instead of FTS5 |
| Object storage client | Azure Blob Storage SDK instead of S3-compatible R2 |
| Worker/ingest service | Consolidated into FastAPI backend (no separate worker for V1) |
| Auth adapter | Python-side auth (or keep NextAuth on frontend, API validates JWT) |
| CLI tool | Python CLI (Typer) |

### What to Replace

| Reference Component | Replacement | Reason |
|---------------------|------------|--------|
| Cloudflare D1 | Azure Database for PostgreSQL Flexible Server | Azure-first; PostgreSQL is more feature-rich |
| Cloudflare R2 | Azure Blob Storage | Azure-first; native SDK |
| Cloudflare Workers | Consolidated into FastAPI backend | No separate worker needed for V1 |
| Railway hosting | Azure App Service | Azure-first; simpler for V1 |
| `wrangler` CLI | Azure CLI + Bicep/Terraform | Infrastructure provisioning |
| Bun runtime (backend) | Python 3.12+ | User requirement |
| D1 HTTP API client | SQLAlchemy / asyncpg / Psycopg 3 | Standard Python DB access |

### What NOT to Carry Over

- Reference project branding, logo, color scheme, product name
- Reference project npm package name and identity
- `bun:sqlite` migration tests and Bun-specific workarounds
- Cloudflare-specific D1 REST API client pattern
- `CLAUDE.md` / `AGENTS.md` pitfalls specific to Bun/Cloudflare
- Dual test runner complexity (Bun + Vitest)
- The specific domain and deployment configuration of the reference project

### What to Defer

- Derived artifacts table (summaries, embeddings, memory candidates)
- Team/org multi-tenancy
- CLI compiled binary distribution

---

## 7. PRD Outline

### Problem Statement

Developers using AI coding assistants (Claude Code, OpenCode, Gemini CLI, etc.) generate thousands of conversation sessions stored in various local formats. There is no unified way to search, replay, or analyze these conversations across tools. Valuable context about AI-assisted decisions, tool invocations, and code changes is effectively lost once the terminal closes.

### Target Users

- **Primary**: Individual developers using 1+ AI coding assistants who want to recall and search past sessions
- **Secondary**: Engineering leads who want to understand AI tool usage patterns across projects
- **Future**: Enterprise compliance teams needing audit trails

### Primary Use Cases

1. **Search recall**: "What did I ask the AI about the auth refactor last week?"
2. **Session replay**: Review the exact conversation flow, including tool calls and code changes
3. **Cross-tool aggregation**: See all AI sessions regardless of which tool generated them
4. **Project analytics**: Understand which projects use the most AI assistance and at what cost
5. **Session organization**: Star important sessions, tag them by topic, archive or delete old ones

### Core Features (V1)

| Feature | Priority | Reference Proven? |
|---------|----------|-------------------|
| CLI source discovery + parsing (5 sources) | P0 | Yes |
| Incremental sync with cursor rollback | P0 | Yes |
| OAuth login (CLI + Web) | P0 | Yes |
| Session list with filters and pagination | P0 | Yes |
| Session replay with markdown + code highlighting | P0 | Yes |
| Full-text search | P0 | Yes |
| Dashboard overview (stats, activity, charts) | P1 | Yes |
| Star and tag management | P1 | Yes |
| Soft delete and trash | P1 | Yes |
| Projects page with analytics | P2 | Yes |
| `Cmd+K` search dialog | P2 | Yes |

### Non-Goals (V1)

- Real-time streaming of active sessions
- Multi-user collaboration or shared sessions
- AI-powered session summarization or semantic search
- Mobile app or mobile-optimized experience
- Self-hosted on-premise deployment option
- Integration with IDE extensions

### V1 Success Criteria

- CLI successfully parses and syncs sessions from 3+ AI tools
- Incremental sync completes in < 30 seconds for typical daily usage
- Full-text search returns results in < 500ms for 10,000+ sessions
- Session replay renders all message types including tool calls and code blocks
- 90%+ unit test coverage on backend
- Successful Azure deployment with < 5 minutes cold start
