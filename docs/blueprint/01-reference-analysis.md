# 01 — Reference Project Analysis

## 1. Reference Project Overview

### What It Does

The reference project is a self-hosted SaaS platform for **replaying and searching AI coding assistant conversation logs**. A CLI tool parses local session files from 5 AI coding tools (Claude Code, Codex CLI, Gemini CLI, OpenCode, VSCode Copilot), incrementally syncs them to the cloud, and a web dashboard provides full-text search and message-by-message replay.

### Core User Flow

1. Developer installs CLI globally
2. CLI authenticates via browser OAuth (Google)
3. CLI `sync` command discovers local AI tool sessions, parses them into a canonical format, and uploads metadata + content
4. Web dashboard displays sessions with search, filtering, replay, tagging, and analytics

### Major Technical Pieces

| Component | Technology | Role |
|-----------|-----------|------|
| `packages/core` | TypeScript (shared) | Types, constants, validators, chunking, title generation |
| `packages/cli` | TypeScript + Bun | Source discovery, 5 parsers, upload pipeline, local config |
| `packages/web` | Next.js 15 (App Router) | Dashboard UI, auth, API routes, D1/R2 client |
| `packages/worker` | Cloudflare Workers | Ingest API, D1 writes, R2 writes, FTS chunk indexing |

### Overall Complexity

- 198 commits, single developer, built in 7 calendar days
- 911+ tests, 98%+ coverage, 90% threshold enforced
- Dual test runners (Bun native + Vitest)
- Split deployment: Railway (web) + Cloudflare (worker + D1 + R2)
- 5 distinct source parsers with different data formats (JSONL, JSON, SQLite, CRDT)

---

## 2. Reference Architecture Breakdown

### Major Modules

```
┌─────────────────────────────────────────────────────────────────┐
│                        packages/core                            │
│  Shared types, constants, validators, chunking, title gen       │
└───────────┬──────────────────────┬──────────────────┬───────────┘
            │                      │                  │
   ┌────────▼────────┐   ┌────────▼────────┐  ┌──────▼──────────┐
   │  packages/cli   │   │  packages/web   │  │ packages/worker │
   │                 │   │                 │  │                 │
   │ 5 parsers       │   │ Next.js 15      │  │ CF Workers      │
   │ Upload pipeline │   │ App Router      │  │ D1 + R2 writes  │
   │ Local config    │   │ shadcn/ui       │  │ FTS5 indexing   │
   │ OAuth login     │   │ NextAuth v5     │  │ Ingest API      │
   └────────┬────────┘   └────────┬────────┘  └──────▲──────────┘
            │                      │                  │
            │              ┌───────▼───────┐          │
            └──────────────► API Routes    ├──────────┘
               uploads     │ (proxy to     │  WORKER_SECRET
                           │  Worker)      │  + X-User-Id
                           └───────────────┘
```

### Runtime Boundaries

- **CLI**: Runs on developer's machine (Bun runtime)
- **Web**: Runs on Railway (Node.js Docker container)
- **Worker**: Runs on Cloudflare Workers (V8 isolates)
- **D1**: Cloudflare-managed SQLite (accessed via HTTP API from web, via bindings from worker)
- **R2**: Cloudflare object storage (accessed via S3 SDK from web, via bindings from worker)

### Data Flow

1. **CLI → Web API → Worker → D1/R2** (write path)
   - CLI parses local files into `CanonicalSession` + `RawSessionArchive`
   - Metadata batch POST (50/batch) → `/api/ingest/sessions` → Worker `/ingest/sessions`
   - Canonical PUT (gzip) → `/api/ingest/content/:key/canonical` → Worker → R2
   - Raw PUT (content-addressed gzip) → presigned R2 URL or proxy route → R2

2. **Browser → Web API → D1/R2** (read path)
   - Dashboard pages fetch `/api/sessions`, `/api/search`, `/api/stats` etc.
   - API routes query D1 via Cloudflare HTTP API
   - Session content fetched from R2 via presigned URLs or content proxy

### External Dependencies

| Dependency | Purpose | Coupling Level |
|-----------|---------|---------------|
| Cloudflare D1 | SQLite database (metadata + FTS) | High — schema, queries, HTTP API |
| Cloudflare R2 | Object storage (session content) | High — key layout, gzip format |
| Cloudflare Workers | Ingest API runtime | High — bindings, wrangler config |
| Railway | Web app hosting | Medium — Docker, env vars |
| Google OAuth | User authentication | Medium — NextAuth provider |
| NextAuth v5 | Auth framework | Medium — JWT strategy, adapter |
| shadcn/ui + Tailwind v4 | UI components + styling | Low — replaceable |
| Recharts | Data visualization | Low — replaceable |
| Shiki | Code syntax highlighting | Low — replaceable |

### Tightly Coupled / Risky Areas

- **D1 HTTP API client** (`lib/d1.ts`): Cloudflare-specific REST API for database access from non-Worker environments
- **Worker ingest logic**: 797-line single file with complex upsert idempotency (4-field hash/version check)
- **5 source parsers**: Each handles a unique format; high maintenance surface area
- **FTS5**: SQLite-specific full-text search with auto-sync triggers; not portable to other DBs
- **Dual storage model**: D1 for metadata + FTS, R2 for full content — architectural decision baked throughout

---

## 2.5 Source Parser Matrix

> Quick reference for each source parser. AI agents implementing parsers should start here.

| Source | Local Path | Format | Cursor Strategy | V1? | Key Risks |
|--------|-----------|--------|----------------|-----|-----------|
| Claude Code | `~/.claude/projects/**/*.jsonl` | JSONL (one event per line) | Byte-offset per file (inode + mtime + size triple-check) | Yes | Content blocks can be string or array; must handle both |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | JSONL rollout files | Byte-offset + last totals + last model | Yes | Top-level `type` field (not `kind`); cumulative token diffs |
| Gemini CLI | `~/.gemini/tmp/*/chats/session-*.json` | Single JSON file per session | Array-index + last totals + last model | Yes | `projectHash` is already a hash; `type: "info"` messages must be skipped |
| OpenCode (SQLite) | `~/.local/share/opencode/opencode.db` | SQLite DB (`session`, `message`, `part` tables) | Watermark (`lastTimeCreated`) + boundary dedup + inode check | Yes | Primary path; cross-source dedup with JSON path; inode change = full rescan; reference had a wiring bug (see `docs/08`) |
| OpenCode (JSON) | `~/.local/share/opencode/storage/{session,message,part}/` | JSON files across 3 directory trees | File triple-check (inode + mtime + size) + message dir mtime | Yes (fallback) | Fallback only — SQLite path is authoritative when both produce data |
| VSCode Copilot | `~/Library/Application Support/Code/User/workspaceStorage/*/chatSessions/*.jsonl` | CRDT append-only JSONL | Byte-offset + request metadata mapping + processed indices | Yes | Most complex parser; CRDT reconstruction (kind=0 Snapshot, kind=1 Set, kind=2 Append); `completedAt` can be numeric epoch |

### Parser Implementation Notes

- All parsers produce **two outputs**: `CanonicalSession` (normalized) + `RawSessionArchive` (verbatim source)
- Raw archives use content-addressed blob paths (`raw/{raw_hash}.json.gz`) — immutable, never overwritten
- Canonical output is overwritten on re-ingest to reflect latest parser logic
- Parse errors must be logged (never silently dropped)
- The reference project uses a dual-driver architecture: `FileDriver` for flat files, `DbDriver` for databases — both are equal citizens in the sync pipeline with identical upload paths and cursor rollback guarantees
- File change detection uses a triple-check (inode + mtime + size) — a file is "unchanged" only when ALL THREE match
- For V1, implement **all 5 sources**: Claude Code, Codex CLI, Gemini CLI, OpenCode (SQLite primary + JSON fallback), VSCode Copilot.

---

## 3. Reference Development Workflow

### Local Setup

```bash
bun install          # installs deps + configures Husky git hooks
bun run dev          # starts Next.js on port 7040
```

- Prerequisites: Bun >= 1.2, Node.js >= 20
- No Docker required for local dev
- Environment variables needed: `AUTH_SECRET`, `AUTH_GOOGLE_*`, `CF_*`, `R2_*`, `WORKER_URL`, `WORKER_SECRET`

### Build and Test

| Command | Runner | Purpose |
|---------|--------|---------|
| `bun run build` | Bun | Build all packages |
| `bun run lint` | tsc | Type check (two separate tsconfig passes) |
| `bun test` | Bun native | 911 tests, includes `bun:sqlite` tests |
| `bunx vitest run` | Node/Vitest | Excludes migration tests |
| `bunx vitest run --coverage` | Node/Vitest | Enforces 90% coverage threshold |

### Git Hooks (Husky)

- **Pre-commit**: `bun run test:coverage` (unit tests + coverage)
- **Pre-push**: `bun run test:coverage` + `bun run lint` (tests + type check)
- No CI/CD pipeline — relies entirely on local hooks

### Configuration Loading

- Web: environment variables (`process.env.*`)
- CLI: `~/.config/<cli-name>/config.json` (API key, device UUID, API URL)
- CLI cursors: `~/.config/<cli-name>/cursors.json` (per-file sync state)
- Worker: Cloudflare bindings (`env.DB`, `env.BUCKET`)

### Deployment Path

- **Web**: Multi-stage Dockerfile (Bun build → Node.js 22-slim runtime), deployed on Railway with Docker builder, `output: "standalone"`
- **Worker**: `wrangler deploy` to Cloudflare Workers
- **CLI**: `bun build --compile` for single-file binary, published to npm
- **Migrations**: `wrangler d1 migrations apply` from `scripts/migrations/`

### Unclear / Missing Areas

- No CI/CD configuration (GitHub Actions, etc.)
- No staging environment documented
- No automated deployment pipeline
- E2E tests planned but not implemented
- No monitoring or alerting setup documented

---

## 4. Git History Interpretation

### Development Timeline

The entire project was built by a single developer over **7 calendar days** (March 12–18, 2026), with 198 commits.

| Date | Commits | Phase |
|------|---------|-------|
| Mar 12 (afternoon) | 15 | Design docs + monorepo scaffolding |
| Mar 13 | ~56 | Parsers + upload pipeline + API routes + dashboard skeleton |
| Mar 14 | ~55 | Production hardening, tags, security, deployment fixes |
| Mar 15 | ~56 | v0.2.0 release, security sweep, UI overhaul, v0.2.1 |
| Mar 18 | 16 | Projects feature, search dialog, v0.3.0 |

### Major Development Phases

**Phase 1 — Design-First Foundation (Day 1, afternoon)**
- 5–6 design documents written before any code
- Monorepo skeleton, core types, D1 migration, worker skeleton, CLI skeleton, web + NextAuth
- Architecture was designed upfront and never changed structurally

**Phase 2 — Data Pipeline (Day 2, morning-afternoon)**
- All 5 source parsers + drivers built in rapid succession (~30 min each)
- Upload engine, content upload, sync command, message chunking
- Worker ingest completed
- Web API routes + D1/R2 clients

**Phase 3 — Dashboard + First Deploy (Day 2, evening — Day 3)**
- Dashboard layout, overview page, session list, session replay, search
- Dockerfile + Railway deployment
- First deployment gauntlet: ~20 deployment-related bug fixes

**Phase 4 — Security + Release (Day 4, morning)**
- FTS5 XSS sanitization, API key hashing, body size limits, gzip bomb defense
- v0.2.0 release

**Phase 5 — UI Polish (Day 4, afternoon)**
- DataTable refactor, soft delete, bulk operations, markdown rendering with Shiki
- Visual rebrand (teal → golden yellow)
- v0.2.1 release

**Phase 6 — Feature Expansion (Day 7)**
- Projects page, `Cmd+K` search dialog
- v0.3.0 release

### Sequencing Worth Borrowing

The reference project follows a pragmatic order that is worth replicating:

1. **Design docs first** — architecture, database schema, API contracts
2. **Data pipeline before UI** — parsers, ingestion, storage
3. **Read path after write path** — API routes, then dashboard pages
4. **Security before release** — hardening pass before v0.2.0
5. **Polish after function** — UI improvements after core features work
6. **Advanced features last** — projects, search dialog, analytics

### High-Churn Areas (Unstable Files)

| File | Touches | Why |
|------|---------|-----|
| `docs/06-implementation-plan.md` | 26 | Living checklist, updated after every milestone |
| `packages/worker/src/index.ts` | 13 | Ingest logic iterated for correctness |
| `packages/web/package.json` | 13 | Constant dependency additions |
| `CLAUDE.md` | 12 | Retrospective documentation of pitfalls |
| `packages/core/src/index.ts` | 11 | Barrel exports updated with every new type |
| `packages/cli/src/commands/sync.ts` | 10 | Central pipeline, many edge cases |

### Key Takeaway

The architecture was stable from day 1 (the 4-package structure never changed), but the **ingest logic** and **deployment configuration** were the most volatile. A new project should invest extra design time in those two areas upfront.
