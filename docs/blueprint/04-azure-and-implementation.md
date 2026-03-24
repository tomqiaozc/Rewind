# 04 — Azure Mapping & Staged Implementation Plan

## 9. Azure Mapping

| Reference Dependency | Azure Replacement | Migration Impact | Difficulty | Notes |
|---------------------|-------------------|-----------------|-----------|-------|
| Cloudflare D1 (SQLite) | Azure Database for PostgreSQL Flexible Server | High — schema rewrite, FTS5→tsvector, query changes | Medium | PostgreSQL is more capable; net positive |
| Cloudflare R2 (S3-compatible) | Azure Blob Storage | Medium — SDK swap, same key layout | Low | `azure-storage-blob` SDK; presigned URLs via SAS tokens |
| Cloudflare Workers | Azure Functions (consumption) or Azure Container Apps | High — runtime + framework change | Medium | FastAPI in container is simpler than Functions for REST APIs |
| Railway (Docker hosting) | Azure App Service or Azure Container Apps | Low — same Docker deployment model | Low | App Service for simplicity; Container Apps for scale |
| Google OAuth (NextAuth) | Same (Google OAuth via NextAuth) | None | None | Runs on frontend; no Azure dependency |
| npm (CLI distribution) | PyPI | Low — different package registry | Low | `pip install rewind` instead of `npm install -g` |
| Husky git hooks | GitHub Actions CI/CD | None — additive | Low | Keep hooks locally, add CI for remote checks |
| `wrangler` CLI | Azure CLI + Bicep | Medium — different IaC paradigm | Medium | Bicep is Azure-native; Terraform is alternative |
| Domain (reference project domain) | New domain (`Pending Confirmation`) | N/A | N/A | `Manual Action Required` |
| No monitoring | Azure Monitor + Application Insights | N/A — new capability | Low | Add from the start |

### Recommended Azure SKUs (Dev/MVP)

| Service | SKU | Monthly Cost (est.) | Notes |
|---------|-----|-------------------|-------|
| Azure Database for PostgreSQL | Burstable B1ms (1 vCore, 2GB) | ~$13 | Flexible Server; auto-scale later |
| Azure Blob Storage | Standard LRS | ~$2 for 50GB | Hot tier for session content |
| Azure App Service (frontend) | B1 (1 vCore, 1.75GB) | ~$13 | Linux, Docker container |
| Azure App Service (backend) | B1 (1 vCore, 1.75GB) | ~$13 | Linux, Docker container |
| Azure Key Vault | Standard | ~$0.03/10K ops | Secrets management |
| Azure Monitor | Pay-as-you-go | ~$2 | Basic logging + alerts |
| **Total estimated** | | **~$43/month** | Dev/MVP tier |

> For production, consider upgrading PostgreSQL to GP_Standard_D2ds_v4 (~$100/mo) and App Service to P1v3 (~$76/mo each).

---

## 10. Staged Implementation Plan

### Phase 0 — Discovery & Setup (Week 1)

**Required Context** (load these sections before starting):
- **03** §Recommended Repo Structure — directory layout to create
- **03** §Suggested Technology Choices — tooling decisions
- **05** §Quick Reference: What to Do First — pre-flight manual actions
- **05** §Azure Setup — decide region and SKU early even if provisioning is deferred
- **05** §Repository & CI/CD — create repo and configure CI secrets

**Objective**: Establish the new project repository, development environment, and foundational infrastructure.

**Key Tasks**:
1. Create new Git repository with monorepo structure
2. Initialize Python backend project (pyproject.toml, FastAPI skeleton, Ruff, mypy)
3. Initialize Next.js frontend project (copy shadcn/ui setup from reference patterns)
4. Set up `docker-compose.yml` for local dev (PostgreSQL, Azurite for Blob emulation)
5. Write initial Alembic migration (users, accounts, api_keys tables)
6. Set up GitHub Actions CI (lint, type check, test)
7. Provision Azure dev environment (PostgreSQL, Blob Storage, App Service) or defer to Phase 5
8. Write AGENTS.md / CLAUDE.md for the new project

**Dependencies**: None

**Risks**:
- Azure subscription and billing setup must be done manually (`Manual Action Required`)
- Domain name must be chosen and registered (`Pending Confirmation`)

**Deliverables**:
- Runnable empty monorepo with working CI
- Local dev stack (docker-compose up)
- Auth tables in PostgreSQL

**Acceptance Criteria**:
- `docker-compose up` starts PostgreSQL + Azurite
- `pytest` runs and passes (even if just health check test)
- `npm run dev` starts Next.js dev server (access via reverse proxy at `https://rewind.dev.example.com`)
- GitHub Actions CI passes on push

---

### Phase 1 — Auth & Core Types (Week 2)

**Required Context** (load these sections before starting):
- **03** §Python Backend Blueprint: Auth — Dual Path — BFF proxy + API key auth code pattern
- **03** §Database Schema — PostgreSQL Port — `users`, `accounts`, `api_keys` table definitions
- **03** §Frontend Reference: Auth — Modify Slightly — NextAuth setup and BFF proxy pattern
- **03** §CLI — Python Port — `login` command flow and libraries
- **05** §Authentication Setup — Google OAuth manual steps (must be done before coding auth)

**Objective**: Implement authentication and establish the shared data model.

**Key Tasks**:
1. Define canonical data model in Python (`backend/src/core/types.py`) — port from reference `packages/core`; this is the single source of truth for both backend and CLI
2. Implement constants, validators, message chunking in Python
3. Set up NextAuth v5 on frontend (Google OAuth, JWT strategy)
4. Implement Python auth: validate BFF proxy headers (`X-User-Id` + `X-Backend-Secret`)
5. Implement API key auth: `rw_` generation, SHA-256 hashing, DB lookup
6. Create CLI auth callback route in Next.js (`/api/auth/cli`)
7. Implement CLI `login` command (Python/Typer — local HTTP server, browser open, key save)
8. Write comprehensive auth tests

**Dependencies**: Phase 0 complete

**Risks**:
- Next.js BFF proxy must reliably forward requests to the Python backend with correct headers
- Google OAuth app registration required (`Manual Action Required`)

**Deliverables**:
- Working Google OAuth login on frontend
- Working CLI login with API key
- Core data model in `backend/src/core/` (shared by backend and CLI via editable install)
- Dual auth (BFF proxy + API key) validated in backend

**Acceptance Criteria**:
- Browser OAuth login works end-to-end
- CLI `login` command opens browser, receives key, saves to config
- Python backend correctly validates both BFF proxy headers and API key headers
- 90%+ test coverage on auth + core modules

---

### Phase 2 — Data Pipeline: Parsers & Ingest (Weeks 3–4)

**Required Context** (load these sections before starting):
- **03** §Python Backend Blueprint: Ingest Service — Port Logic — idempotent upsert decision tree
- **03** §Python Backend Blueprint: Blob Storage Layout — canonical + raw key format
- **03** §Python Backend Blueprint: Search Service — PostgreSQL FTS — tsvector + ts_headline pattern
- **03** §Database Schema — PostgreSQL Port — `sessions`, `messages`, `message_chunks` tables
- **03** §API Endpoints — ingest routes (POST/PUT)
- **01** §2 (Reference Architecture) — parser format details and edge cases
- **01** §2.5 (Source Parser Matrix) — idempotent ingest, message chunking, dual storage

**Objective**: Build the CLI sync pipeline and backend ingest service.

**Key Tasks**:
1. Implement file change detection utility (inode/mtime/size or watchfiles)
2. Implement cursor store (persistent per-file sync state in `~/.config/rewind/`)
3. **Port 3 parsers** from reference to Python:
   - Claude Code parser (JSONL, byte-offset cursor)
   - OpenCode parser (JSON files + SQLite DB, watermark cursor)
   - Gemini CLI parser (JSON files, array-index cursor)
4. Implement driver registry (auto-detect available sources)
5. Implement upload engine (batch metadata POST, gzip content PUT, retry with backoff)
6. Implement backend ingest API:
   - `POST /api/ingest/sessions` — batch metadata upsert
   - `PUT /api/ingest/content/{key}/canonical` — canonical content to Blob
   - `PUT /api/ingest/content/{key}/raw` — raw content to Blob (content-addressed)
7. Implement idempotent upsert logic (4-field version check)
8. Implement message chunking + FTS indexing (PostgreSQL tsvector)
9. Implement Alembic migration for sessions, messages, message_chunks tables
10. Implement CLI `sync` command orchestration
11. Implement gzip decompression with size limits (bomb defense)

**Dependencies**: Phase 1 complete (auth + data model)

**Risks**:
- Parser correctness is critical — each source format has edge cases documented in reference `docs/04-parsers.md`
- OpenCode SQLite parser requires careful cursor management (reference had a wiring bug — `docs/08-opencode-sqlite-driver-bug.md`)
- Gzip bomb defense must be ported (256MB decompressed limit)

**Deliverables**:
- Working `rewind sync` for 3 V1 sources
- Backend ingest API with idempotent upsert
- PostgreSQL FTS indexing on ingested content
- Blob Storage with canonical + raw content

**Acceptance Criteria**:
- CLI syncs real local sessions from Claude Code, OpenCode, and Gemini
- Incremental re-sync uploads 0 new sessions
- Backend correctly rejects conflicting parser versions (409)
- FTS index is populated and queryable
- 90%+ test coverage on parsers, ingest, chunking

---

### Phase 3 — Dashboard & Search (Weeks 5–6)

**Required Context** (load these sections before starting):
- **03** §Frontend Reference — entire section (Stack, Page Structure, Layout Pattern, Component Patterns, Data Fetching)
- **03** §Frontend Reference: What NOT to Copy — avoid reference branding and direct D1/R2 access
- **03** §API Endpoints — read routes (GET sessions, search, stats, filters)
- **03** §Python Backend Blueprint: Search Service — backend search contract the frontend calls

**Objective**: Build the web dashboard with session browsing, replay, and search.

**Key Tasks**:
1. Implement backend read API routes:
   - `GET /api/sessions` — list with keyset/offset pagination, filters, sorting
   - `GET /api/sessions/{id}` — session detail
   - `GET /api/sessions/{id}/content` — content from Blob (presigned URL or proxy)
   - `GET /api/search` — FTS search with snippet extraction
   - `GET /api/stats` — dashboard overview statistics
   - `GET /api/sessions/filters` — distinct values for filter dropdowns
2. Build frontend layout:
   - AppShell (sidebar + header + content island) — adapt from reference patterns
   - Theme toggle (dark/light/system)
   - Navigation links
3. Build frontend pages:
   - Dashboard overview (stat cards, activity heatmap, source chart, recent sessions)
   - Session list (DataTable, filters, pagination)
   - Session replay (message bubbles, tool calls, markdown/code rendering, j/k nav)
   - Search page (debounced FTS, snippet highlighting)
4. Implement frontend API client layer (fetch wrapper for backend calls)
5. Style with new branding (colors, fonts — `Pending Confirmation`)

**Dependencies**: Phase 2 complete (data in DB + Blob)

**Risks**:
- Session replay rendering is complex (multiple content types: text, code, tool calls)
- FTS snippet sanitization is security-critical (XSS via `<mark>` tags)

**Deliverables**:
- Working dashboard with all core pages
- Session replay with code highlighting
- Full-text search with highlighted snippets
- Responsive layout (desktop + mobile)

**Acceptance Criteria**:
- Dashboard shows accurate stats from ingested data
- Session list supports filtering by source, project, date range
- Session replay renders all message types including tool calls
- Search returns relevant results with highlighted snippets
- Pages load in < 2 seconds
- Mobile layout is functional

---

### Phase 4 — Organization & Polish (Week 7)

**Required Context** (load these sections before starting):
- **03** §Frontend Reference: Component Patterns — DataTable, bulk actions, optimistic updates
- **03** §Database Schema — PostgreSQL Port — `tags`, `session_tags` tables
- **03** §API Endpoints — tags CRUD, projects, batch operations
- **03** §Frontend Reference: Page Structure — projects page, settings page, trash page

**Objective**: Add session management features and UI polish.

**Key Tasks**:
1. Implement tags system:
   - Alembic migration for tags + session_tags
   - Backend CRUD API for tags
   - Backend API for session-tag associations
   - Frontend tag management UI (settings page, color picker)
   - Frontend tag display on session list and detail
2. Implement star/unstar:
   - Backend API endpoint
   - Frontend optimistic toggle
3. Implement soft delete + trash:
   - Backend: `deleted_at` timestamp, filter deleted from normal queries
   - Frontend: trash page with restore, bulk operations
4. Implement bulk operations:
   - Backend batch API (delete, restore, star, unstar)
   - Frontend DataTable bulk action bar
5. Implement `Cmd+K` search dialog
6. Implement projects page:
   - Backend projects API with aggregates
   - Frontend project cards, ranking chart, activity chart
7. Implement CLI `status` command
8. UI polish: loading skeletons, animations, responsive tweaks

**Dependencies**: Phase 3 complete (dashboard works)

**Risks**:
- Bulk operations on large datasets need DB optimization
- Recharts data field naming must avoid React reserved props (`ref`, `key`)

**Deliverables**:
- Full V1 feature parity with the reference project's core experience
- Polished, branded UI
- CLI with login, sync, status commands

**Acceptance Criteria**:
- Tags can be created, assigned, filtered by
- Star toggle works with optimistic update
- Soft delete sends to trash, restore works
- Bulk operations work for > 100 selected items
- `Cmd+K` search dialog works globally
- Projects page shows accurate aggregates

---

### Phase 5 — Deployment & Hardening (Week 8)

**Required Context** (load these sections before starting):
- **04** §Azure Mapping — full service mapping and recommended SKUs
- **05** — entire file (all manual actions, launch blockers, pending confirmations)
- **03** §Recommended Repo Structure — `infra/` directory layout for Bicep/Terraform
- **03** §Runtime Boundaries — deployment architecture diagram

**Objective**: Deploy to Azure and harden for production use.

**Key Tasks**:
1. Write Dockerfiles for frontend and backend
2. Write Bicep/Terraform IaC for Azure resources:
   - PostgreSQL Flexible Server
   - Blob Storage account + containers
   - App Service (frontend) + App Service (backend)
   - Key Vault for secrets
   - Application Insights for monitoring
3. Set up GitHub Actions deploy workflow (CI → build → push → deploy)
4. Configure custom domain + TLS (`Manual Action Required`)
5. Security hardening:
   - Rate limiting on ingest endpoints
   - Request body size limits (50MB content, 2MB metadata)
   - Gzip bomb defense (256MB decompressed limit)
   - Content-Length required (411 on missing)
   - CORS configuration
   - Secure headers (CSP, HSTS)
6. Set up Azure Monitor alerts (error rate, latency, DB connections)
7. Run load test with realistic data volume
8. Write production runbook

**Dependencies**: Phase 4 complete (all features working locally)

**Risks**:
- First deployment typically surfaces environment-specific issues (the reference had ~20 deployment fixes)
- PostgreSQL connection pooling needs tuning
- Cold start times on App Service B1 tier

**Deliverables**:
- Production deployment on Azure
- CI/CD pipeline
- Monitoring and alerting
- Production runbook

**Acceptance Criteria**:
- Production deployment accessible via custom domain
- CI/CD deploys on merge to main
- Health check endpoint returns 200
- Monitoring alerts fire on error spike
- Cold start < 5 seconds
- Ingest handles 100 concurrent sessions without errors

---

### Phase 6 — Expansion (Weeks 9+)

**Required Context** (load these sections before starting):
- **03** §Testing Strategy — E2E testing with Playwright

**Objective**: Add remaining parsers and advanced features.

**Key Tasks**:
1. E2E test suite (Playwright)
2. CLI compiled binary distribution (PyInstaller or Nuitka)
3. Team/org features (multi-user, shared sessions, RBAC)
4. AI features: session summaries, embeddings, semantic search
5. Export and compliance features
6. Additional OAuth providers (GitHub, Azure AD)
7. Performance optimization (caching, CDN, read replicas)

**Dependencies**: Phase 5 complete (production deployment)

**Risks**:
- VSCode Copilot CRDT parser is the most complex parser by far
- Multi-tenancy requires significant schema and auth changes

**Deliverables**:
- 2 additional source parsers beyond V1
- E2E test coverage
- Advanced features per roadmap

**Acceptance Criteria**:
- All 5 source parsers sync successfully
- E2E tests cover critical user flows
- No regression in performance or reliability
