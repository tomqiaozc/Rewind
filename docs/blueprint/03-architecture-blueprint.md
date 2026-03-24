# 03 — Architecture Blueprint

## 8. Architecture Blueprint

### Recommended Repo Structure

```
rewind/                              # new project root (monorepo)
├── README.md
├── pyproject.toml                   # Python project config (uv/poetry)
├── docker-compose.yml               # local dev: PostgreSQL, Azurite, backend
├── Makefile                         # common dev commands
├── .github/
│   └── workflows/
│       ├── ci.yml                   # lint + test + type check
│       └── deploy.yml               # deploy to Azure
│
├── packages/
│   └── web/                         # Next.js 15 frontend (keeps reference approach)
│       ├── package.json
│       ├── next.config.ts
│       ├── tsconfig.json
│       ├── tailwind.config.ts       # or CSS v4 config
│       ├── components.json          # shadcn/ui
│       ├── Dockerfile
│       └── src/
│           ├── app/                 # App Router pages
│           ├── components/          # UI components
│           ├── lib/                 # helpers (api client, auth, format)
│           └── hooks/               # React hooks
│
├── backend/                         # Python backend (replaces worker + API routes)
│   ├── pyproject.toml
│   ├── alembic.ini                  # DB migrations
│   ├── alembic/
│   │   └── versions/               # migration scripts
│   ├── Dockerfile
│   └── src/
│       ├── main.py                  # FastAPI app entry
│       ├── config.py                # settings (pydantic-settings)
│       ├── auth/                    # BFF Proxy + API key auth
│       ├── api/                     # route handlers
│       │   ├── sessions.py
│       │   ├── search.py
│       │   ├── stats.py
│       │   ├── tags.py
│       │   ├── projects.py
│       │   └── ingest.py
│       ├── models/                  # SQLAlchemy models
│       ├── schemas/                 # Pydantic request/response schemas
│       ├── services/                # business logic
│       │   ├── ingest.py            # idempotent upsert logic
│       │   ├── search.py            # FTS query builder
│       │   ├── storage.py           # Azure Blob operations
│       │   ├── sessions.py          # Session listing/detail
│       │   ├── stats.py             # Dashboard aggregates
│       │   ├── tags.py              # Tag CRUD
│       │   └── projects.py          # Project grouping
│       ├── db/                      # database helpers
│       └── core/                    # shared types, constants, validators (single source of truth)
│           ├── types.py             # CanonicalSession, CanonicalMessage
│           ├── constants.py         # PARSER_REVISION, SCHEMA_VERSION
│           ├── validators.py
│           └── chunking.py          # message chunking for FTS
│
├── cli/                             # Python CLI (replaces packages/cli)
│   ├── pyproject.toml
│   └── src/
│       ├── main.py                  # CLI entry (Typer/Click)
│       ├── commands/
│       │   ├── sync.py
│       │   ├── login.py
│       │   └── status.py
│       ├── parsers/                 # source parsers
│       │   ├── claude.py
│       │   ├── opencode.py
│       │   ├── gemini.py
│       │   ├── codex.py
│       │   └── copilot.py
│       ├── drivers/                 # file + DB drivers
│       ├── upload/                  # upload engine + content upload
│       ├── config/                  # local config manager
│       └── utils/                   # file change detection, paths
│
│   # NOTE: No separate shared/ package. backend/src/core/ is the single source
│   # of truth for types, constants, and validators. CLI imports these via a
│   # shared Python package installed as an editable dependency:
│   #   cli/pyproject.toml → dependencies = ["rewind-core @ file:../backend"]
│   # Do NOT duplicate types into cli/src/types.py — that creates drift.
│
└── infra/                           # Azure infrastructure-as-code
    ├── main.bicep                   # or Terraform
    ├── modules/
    └── parameters/
        ├── dev.bicepparam
        └── prod.bicepparam
```

### Runtime Boundaries

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Developer's Machine                               │
│  ┌──────────────┐                                                    │
│  │   CLI (Python)│──────────────────────────────┐                    │
│  │   Typer/Click │                              │                    │
│  └──────────────┘                               │                    │
│                                                  ▼                    │
│                            ┌─────────────────────────────────┐       │
│                            │  Azure App Service / Container   │       │
│                            │  ┌───────────────────────────┐   │       │
│                            │  │  Next.js Frontend         │   │       │
│  ┌──────────┐              │  │  (SSR + static)           │   │       │
│  │ Browser  │◄─────────────│  │  Auth (NextAuth v5)       │   │       │
│  └──────────┘              │  └───────────┬───────────────┘   │       │
│                            │              │ fetch /api/*      │       │
│                            │  ┌───────────▼───────────────┐   │       │
│                            │  │  Python Backend (FastAPI)  │   │       │
│                            │  │  REST API                  │   │       │
│                            │  └───────────┬───────────────┘   │       │
│                            └──────────────┼───────────────────┘       │
│                                           │                           │
│              ┌────────────────────────────┼────────────────────┐      │
│              │            Azure           │                    │      │
│              │  ┌────────────────┐   ┌────▼─────────────┐     │      │
│              │  │ Azure Blob     │   │ Azure PostgreSQL  │     │      │
│              │  │ Storage        │   │ Flexible Server   │     │      │
│              │  └────────────────┘   └──────────────────┘     │      │
│              └────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────┘
```

### Frontend Responsibilities

The frontend handles:
- User-facing pages (dashboard, sessions, replay, search, projects, settings, trash)
- Authentication flow (NextAuth v5 with Google OAuth)
- Client-side state (filters, pagination, search debounce)
- Data visualization (charts, heatmaps)
- CLI auth callback endpoint

The frontend does **NOT** handle:
- Database queries (delegated to Python backend API)
- Object storage access (delegated to Python backend API)
- Ingest logic (delegated to Python backend API)
- Business logic (pure display layer)

### Backend Responsibilities

The Python backend handles:
- All database queries (PostgreSQL via SQLAlchemy/asyncpg)
- All object storage operations (Azure Blob via azure-storage-blob SDK)
- Ingest API (receive CLI uploads, validate, store)
- Full-text search (PostgreSQL `tsvector` or Azure AI Search)
- Auth validation (verify BFF proxy headers, verify API key hash)
- Session CRUD, tag management, stats aggregation
- Content chunking and FTS indexing

### Data and Infra Responsibilities

- **PostgreSQL**: Session metadata, messages, message chunks, tags, users, FTS indexes
- **Azure Blob Storage**: Session content (canonical.json.gz, raw/{hash}.json.gz)
- **Azure App Service**: Host both frontend and backend (or separate services)
- **Azure Key Vault**: Secrets management (OAuth secrets, DB connection strings)

### Suggested Technology Choices

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend framework | Next.js 15 (App Router) | Same as reference; proven for this use case |
| Frontend UI | Tailwind CSS v4 + shadcn/ui | Same as reference; rapid, consistent UI |
| Frontend charts | Recharts | Same as reference; activity heatmap, source charts |
| Frontend auth | NextAuth v5 (Google OAuth) | Same as reference; proven flow |
| Backend framework | FastAPI | Async Python, auto-docs, Pydantic validation |
| Backend ORM | SQLAlchemy 2.0 (async) | Industry standard, Alembic migrations |
| Backend DB driver | asyncpg | High-performance async PostgreSQL |
| Backend validation | Pydantic v2 | Request/response schemas, settings |
| Database | PostgreSQL 16 (Azure Flexible Server) | Full-text search, JSONB, mature ecosystem |
| Object storage | Azure Blob Storage | Azure-native, gzip support |
| Secrets | Azure Key Vault | Secure secrets management |
| CLI framework | Typer (built on Click) | Modern Python CLI with auto-help |
| CLI HTTP | httpx | Async HTTP client with retry |
| Testing (backend) | pytest + pytest-asyncio | Standard Python testing |
| Testing (frontend) | Vitest | Same as reference |
| Linting | Ruff (Python), ESLint (TS) | Fast, opinionated |
| Type checking | mypy or pyright (Python), tsc (TS) | Strict typing |
| CI/CD | GitHub Actions | Standard, Azure integration |
| IaC | Bicep or Terraform | Azure resource provisioning |

---

## Frontend Reference

> This section documents which parts of the reference project's frontend are worth borrowing for the new project.

### Stack and Tooling — Adopt As-Is

The reference project's frontend stack is well-chosen and should be kept:

- **Next.js 15 App Router** with `output: "standalone"` for containerized deployment
- **Tailwind CSS v4** with HSL-based custom properties for theming
- **shadcn/ui (new-york style)** for consistent, accessible components
- **Recharts** for data visualization
- **react-markdown + remark-gfm + Shiki** for code-rich content rendering
- **TanStack React Table v8** for data tables with server-side sorting
- **Radix UI primitives** (Dialog, Tooltip, HoverCard, etc.)
- **Lucide icons**

### Page Structure — Adopt Pattern

| Reference Route | New Project Route | Borrow? |
|----------------|-------------------|---------|
| `/login` | `/login` | Yes — Google OAuth sign-in page |
| `/dashboard` | `/dashboard` | Yes — stat cards, activity heatmap, source chart, recent items, top projects |
| `/dashboard/sessions` | `/dashboard/sessions` | Yes — DataTable with filters, pagination, bulk actions |
| `/dashboard/sessions/[id]` | `/dashboard/sessions/[id]` | Yes — session replay with message bubbles, tool calls, code blocks |
| `/dashboard/search` | `/dashboard/search` | Yes — FTS search with snippet highlighting |
| `/dashboard/projects` | `/dashboard/projects` | Yes — project cards, ranking chart, drill-down |
| `/dashboard/trash` | `/dashboard/trash` | Yes — soft-deleted items with restore |
| `/dashboard/settings/tags` | `/dashboard/settings/tags` | Yes — tag CRUD with color picker |
| `/` (landing) | `/` | No — create new landing page with new branding |

### Layout Pattern — Adopt

- **AppShell**: Sidebar + header + floating content island with rounded card styling
- **Collapsible sidebar**: 68px collapsed / 260px expanded, icon-only when collapsed
- **Mobile**: Overlay sidebar with backdrop blur, hamburger toggle
- **Breadcrumbs**: Auto-generated from pathname
- **Theme**: Dark/light/system toggle, FOUC prevention script in root layout

### Component Patterns — Adopt

| Pattern | Reference Implementation | Notes for New Project |
|---------|------------------------|----------------------|
| DataTable | TanStack v8, manual server-side sorting, skeleton rows, checkbox selection | Keep pattern, connect to Python API |
| Bulk Actions | Floating bar on selection, "select all matching" mode | Keep pattern |
| Session Replay | Role-based message bubbles, tool call accordion, `j/k` nav, timestamp gaps | Keep pattern, adjust styling |
| Activity Heatmap | CSS grid (52×7), green color scale, custom tooltip | Keep pattern, change colors |
| Search Dialog | `Cmd+K` Radix Dialog, 300ms debounce, keyboard nav | Keep pattern |
| Stat Cards | Animated count-up, icon, trend indicator | Keep pattern |
| Loading States | Skeleton patterns everywhere, no spinners | Keep pattern |
| Optimistic Updates | Star toggle with rollback | Keep pattern |

### Data Fetching — Modify

The reference project uses **client components** that fetch from Next.js API routes, which then call Cloudflare D1 HTTP API.

**New project should:**
- Keep client components fetching from API routes
- API routes proxy to the Python backend instead of calling D1 directly
- OR: client components call the Python API directly (if CORS is configured)
- **Recommended approach**: Next.js API routes act as a thin proxy/BFF to the Python backend. This keeps auth cookie handling in Next.js and avoids CORS complexity.

```
Browser → Next.js API Route → Python Backend API → PostgreSQL / Blob Storage
```

### Auth — Modify Slightly

- Keep NextAuth v5 with Google OAuth and JWT strategy
- Keep dual auth (BFF proxy header for browser, API key for CLI)
- **NextAuth is the sole session issuer** — it creates JWTs on login.
- **BFF Proxy Pattern (Required)**: Because NextAuth v5 uses encrypted JWE tokens by default, decrypting them in Python is complex and brittle. Instead, you must use the BFF (Backend-for-Frontend) proxy pattern: Next.js API routes validate the session via `auth()` and proxy requests to the Python backend, attaching a trusted `X-User-Id` header (and a shared secret to prevent spoofing). The Python backend never reads the NextAuth cookie directly. This matches the reference project's Worker architecture.
- CLI auth callback route stays in Next.js (`/api/auth/cli`)
- Python backend validates `Authorization: Bearer rw_...` by hashing and looking up in DB
- **Critical**: Dev CLI auth must use a real HTTPS dev domain (e.g., `https://rewind.dev.example.com`), NOT `http://localhost:3000`. Session cookies are bound to the domain; `auth()` returns null on localhost. Use Caddy or similar reverse proxy with mkcert TLS for local dev.

### What NOT to Copy from Frontend

- Reference project branding (golden yellow, Caveat font logo, product name)
- Reference project product-specific copy and information architecture
- Reference project domain references
- D1 HTTP API client (`lib/d1.ts`) — replaced by calls to Python backend
- R2 direct access from frontend (`lib/r2.ts`) — replaced by Python backend presigned URLs
- `lib/ingest.ts` proxy helpers — replaced by Python backend endpoints

---

## Python Backend Blueprint

> This section documents what backend capabilities from the reference project need to be rebuilt in Python.

### Overview

The reference project's backend logic is split across two TypeScript packages:
- `packages/worker` (797 lines) — Cloudflare Worker for ingest
- `packages/web/src/app/api/` + `packages/web/src/lib/` — Next.js API routes and query builders

The new project consolidates all backend logic into a single **FastAPI application**.

### Capability Mapping

| Reference Capability | Reference Location | Python Equivalent |
|---------------------|-------------------|-------------------|
| Session metadata ingest | `worker/src/index.ts` POST `/ingest/sessions` | `backend/src/api/ingest.py` |
| Canonical content upload | `worker/src/index.ts` PUT `/ingest/content/:key/canonical` | `backend/src/api/ingest.py` |
| Raw content upload | `worker/src/index.ts` PUT `/ingest/content/:key/raw` | `backend/src/api/ingest.py` |
| Raw upload confirm | `web/src/app/api/ingest/confirm-raw/route.ts` | `backend/src/api/ingest.py` |
| Content retrieval | `worker/src/index.ts` GET `/content/:key` | `backend/src/api/sessions.py` |
| Session listing | `web/src/lib/sessions.ts` | `backend/src/services/sessions.py` |
| Session detail | `web/src/lib/session-detail.ts` | `backend/src/services/sessions.py` |
| Full-text search | `web/src/lib/search.ts` | `backend/src/services/search.py` |
| Dashboard stats | `web/src/lib/stats.ts` | `backend/src/services/stats.py` |
| Tag CRUD | `web/src/lib/tags.ts` | `backend/src/services/tags.py` |
| Project queries | `web/src/lib/projects.ts` | `backend/src/services/projects.py` |
| User auth (OAuth adapter) | `web/src/lib/auth-adapter.ts` | Stays in Next.js (NextAuth) — Python trusts BFF proxy |
| CLI auth (API key) | `web/src/lib/cli-auth.ts` | `backend/src/auth/api_key.py` (key generation + hash storage) |
| D1 client | `web/src/lib/d1.ts` | SQLAlchemy async session |
| R2 client | `web/src/lib/r2.ts` | `azure.storage.blob` SDK |
| Ingest proxy | `web/src/lib/ingest.ts` | Not needed — backend handles directly |
| Format utilities | `web/src/lib/format.ts` | Keep in frontend (display-only) |

### Database Schema — PostgreSQL Port

The reference D1 schema maps to PostgreSQL with these changes:

```sql
-- Users (reference: D1 users table)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    email TEXT UNIQUE NOT NULL,
    email_verified TIMESTAMPTZ,
    image TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- OAuth accounts (reference: D1 accounts table)
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    type TEXT NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    expires_at BIGINT,
    token_type TEXT,
    scope TEXT,
    id_token TEXT,
    UNIQUE(provider, provider_account_id)
);

-- API keys (reference: D1 api_keys from migration 003)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,         -- SHA-256 of rw_... key
    device_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

-- Sessions (reference: D1 sessions table, 30+ columns)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_key TEXT NOT NULL,
    source TEXT NOT NULL,                   -- claude, opencode, gemini, codex, copilot
    -- temporal
    started_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    snapshot_at TIMESTAMPTZ NOT NULL,
    -- counts
    user_messages INTEGER DEFAULT 0,
    assistant_messages INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    -- tokens
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_cached_tokens BIGINT DEFAULT 0,
    -- context
    project_ref TEXT,
    project_name TEXT,
    model TEXT,
    title TEXT,
    summary TEXT,
    -- content references (Blob Storage keys)
    content_key TEXT,
    content_size BIGINT,
    raw_key TEXT,
    raw_size BIGINT,
    -- versioning (idempotent ingest)
    content_hash TEXT,
    raw_hash TEXT,
    parser_revision INTEGER NOT NULL,
    schema_version INTEGER NOT NULL,
    ingested_at TIMESTAMPTZ,
    -- user organization
    is_starred BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,                -- soft delete
    -- timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, session_key)
);

-- Messages (reference: D1 messages table)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,                     -- user, assistant, system, tool
    ordinal INTEGER NOT NULL,
    -- tool metadata
    tool_name TEXT,
    tool_call_id TEXT,
    tool_status TEXT,
    -- tokens
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    -- timing
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    UNIQUE(session_id, ordinal)
);

-- Message chunks for FTS (reference: D1 message_chunks + chunks_fts)
CREATE TABLE message_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    tool_context TEXT,                      -- searchable tool call info on chunk 0
    UNIQUE(message_id, chunk_index)
);

-- FTS: PostgreSQL tsvector column + GIN index (replaces SQLite FTS5)
ALTER TABLE message_chunks
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(content, '') || ' ' || coalesce(tool_context, ''))
    ) STORED;

CREATE INDEX idx_chunks_fts ON message_chunks USING GIN(search_vector);

-- Tags (reference: D1 tags + session_tags from migration 002)
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#6b7280',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, name)
);

CREATE TABLE session_tags (
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY(session_id, tag_id)
);
```

**Key differences from reference D1 schema:**
- UUID primary keys instead of TEXT (better for distributed systems)
- `TIMESTAMPTZ` instead of TEXT ISO strings
- `GENERATED ALWAYS AS ... STORED` tsvector instead of FTS5 virtual table + triggers
- Foreign key constraints with `ON DELETE CASCADE`
- No need for D1's 1MB/row workaround (PostgreSQL handles large rows natively)

### Title Generation - Exact Port

The reference project derives a title from the first user message and optional project name. Port this exactly so replay lists and search results behave the same.

Rules:
- `MAX_TITLE_LENGTH = 80`
- Normalize whitespace in the first user message: collapse all whitespace to single spaces, then trim
- If `project_name` exists, split by `/` and use the last non-empty path segment as a prefix: `[segment] `
- Subtract the prefix length from the 80-character budget
- Truncate on a word boundary when possible; otherwise hard-truncate
- Append `...` when truncation happens
- If there is no non-empty first user message, return `null`

```python
MAX_TITLE_LENGTH = 80


def build_title(project_name: str | None, first_user_message: str | None) -> str | None:
    if not first_user_message:
        return None

    message = re.sub(r"\s+", " ", first_user_message).strip()
    if not message:
        return None

    prefix = ""
    if project_name:
        parts = [part for part in project_name.split("/") if part]
        if parts:
            prefix = f"[{parts[-1]}] "

    budget = MAX_TITLE_LENGTH - len(prefix)
    if budget <= 0:
        return truncate_at_word(message, MAX_TITLE_LENGTH)

    return prefix + truncate_at_word(message, budget)
```

### Ingest Service - Port Logic

The reference ingest flow is not a single decision tree. It is three separate write paths that must stay distinct:

1. `POST /api/ingest/sessions` - batch metadata upsert only
2. `PUT /api/ingest/content/{session_key}/canonical` - canonical gzip upload + metadata update
3. Raw upload path:
   - `POST /api/ingest/presign` -> return Blob SAS URL
   - client `PUT`s raw gzip directly to Blob Storage
   - `POST /api/ingest/content/{session_key}/raw/confirm` -> persist `raw_key`, `raw_size`, `raw_hash`
   - fallback: `PUT /api/ingest/content/{session_key}/raw` proxy upload when direct upload fails

Do not collapse these into one endpoint. The metadata upsert does not have a separate "raw-only update" branch.

#### Metadata Upsert

The reference worker uses a single `INSERT ... ON CONFLICT DO UPDATE ... WHERE` statement guarded by both version checks and content-change checks.

```python
stmt = insert(Session).values(
    id=session_id,
    user_id=user_id,
    session_key=snapshot.session_key,
    source=snapshot.source,
    started_at=snapshot.started_at,
    last_message_at=snapshot.last_message_at,
    duration_seconds=snapshot.duration_seconds,
    snapshot_at=snapshot.snapshot_at,
    user_messages=snapshot.user_messages,
    assistant_messages=snapshot.assistant_messages,
    total_messages=snapshot.total_messages,
    total_input_tokens=snapshot.total_input_tokens,
    total_output_tokens=snapshot.total_output_tokens,
    total_cached_tokens=snapshot.total_cached_tokens,
    project_ref=snapshot.project_ref,
    project_name=snapshot.project_name,
    model=snapshot.model,
    title=snapshot.title,
    content_hash=snapshot.content_hash,
    raw_hash=snapshot.raw_hash,
    parser_revision=snapshot.parser_revision,
    schema_version=snapshot.schema_version,
    ingested_at=func.now(),
)

stmt = stmt.on_conflict_do_update(
    index_elements=[Session.user_id, Session.session_key],
    set_={
        "source": stmt.excluded.source,
        "started_at": stmt.excluded.started_at,
        "last_message_at": stmt.excluded.last_message_at,
        "duration_seconds": stmt.excluded.duration_seconds,
        "snapshot_at": stmt.excluded.snapshot_at,
        "user_messages": stmt.excluded.user_messages,
        "assistant_messages": stmt.excluded.assistant_messages,
        "total_messages": stmt.excluded.total_messages,
        "total_input_tokens": stmt.excluded.total_input_tokens,
        "total_output_tokens": stmt.excluded.total_output_tokens,
        "total_cached_tokens": stmt.excluded.total_cached_tokens,
        "project_ref": stmt.excluded.project_ref,
        "project_name": stmt.excluded.project_name,
        "model": stmt.excluded.model,
        "title": stmt.excluded.title,
        "content_hash": stmt.excluded.content_hash,
        "raw_hash": stmt.excluded.raw_hash,
        "parser_revision": stmt.excluded.parser_revision,
        "schema_version": stmt.excluded.schema_version,
        "ingested_at": func.now(),
        "updated_at": func.now(),
    },
    where=and_(
        stmt.excluded.parser_revision >= Session.parser_revision,
        stmt.excluded.schema_version >= Session.schema_version,
        or_(
            stmt.excluded.content_hash != Session.content_hash,
            stmt.excluded.raw_hash != Session.raw_hash,
            stmt.excluded.parser_revision > Session.parser_revision,
            stmt.excluded.schema_version > Session.schema_version,
        ),
    ),
)
```

Important behavior:
- Same hashes + same versions -> no-op update
- Older parser/schema version cannot overwrite newer data
- `deleted_at` is preserved during re-ingest
- `content_key`, `content_size`, `raw_key`, and `raw_size` are updated by separate content-upload handlers, not by metadata upsert

#### Canonical Upload

Canonical upload is a separate endpoint that:
- requires `Content-Length`
- rejects oversized compressed payloads
- streams gunzip with a 256 MB decompressed ceiling
- verifies the session already exists
- returns `404` if metadata was not ingested first
- uploads to `{user_id}/{session_key}/canonical.json.gz`
- updates `content_key`, `content_size`, `content_hash`, and `updated_at`

#### Raw Upload

Preferred raw upload flow for Azure Blob Storage:

1. CLI calls `POST /api/ingest/presign` with `session_key` and `raw_hash`
2. Backend returns a short-lived SAS URL for `{user_id}/{session_key}/raw/{raw_hash}.json.gz`
3. CLI uploads gzip bytes directly to Blob Storage using the SAS URL
4. CLI calls `POST /api/ingest/content/{session_key}/raw/confirm` with `raw_hash` and `raw_size`
5. Backend verifies the blob exists, then updates `raw_key`, `raw_size`, `raw_hash`, and `updated_at`

Fallback path:
- if direct upload fails for non-auth reasons, CLI may fall back to `PUT /api/ingest/content/{session_key}/raw`
- this proxy upload must enforce the same size limits and must also return `404` if the session does not already exist

### Blob Storage Layout — Same Pattern

```
{user_id}/{session_key}/canonical.json.gz        # overwritten on re-ingest
{user_id}/{session_key}/raw/{raw_hash}.json.gz   # immutable, content-addressed
```

Use `azure.storage.blob.aio.BlobServiceClient` for async operations.

### Search Service — PostgreSQL FTS

```python
# backend/src/services/search.py

async def search_sessions(
    db: AsyncSession,
    user_id: str,
    query: str,
    source_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[SearchResult]:
    """
    Port of reference FTS5 search.
    Uses PostgreSQL ts_query + ts_headline for snippet extraction.
    Crucial: Must return message_id, ordinal, and chunk_index so the
    frontend can jump directly to the exact message in the replay view.
    """
    tsquery = func.plainto_tsquery("english", query)

    stmt = (
        select(
            MessageChunk.session_id,
            MessageChunk.message_id,
            MessageChunk.chunk_index,
            Message.ordinal,
            Session.title,
            Session.source,
            Session.started_at,
            func.ts_headline(
                "english",
                MessageChunk.content,
                tsquery,
                r"StartSel=\x01, StopSel=\x02, MaxWords=40, MinWords=20",
            ).label("snippet"),
        )
        .join(Session, MessageChunk.session_id == Session.id)
        .join(Message, MessageChunk.message_id == Message.id)
        .where(
            Session.user_id == user_id,
            Session.deleted_at.is_(None),
            MessageChunk.search_vector.op("@@")(tsquery),
        )
    )
    ...
```

Do not emit raw `ts_headline(... StartSel=<mark> ...)` output directly to the browser. The safe pattern is:
- use control characters for `StartSel` and `StopSel`
- HTML-escape the full snippet string
- replace the trusted control characters with `<mark>` and `</mark>`

```python
SNIPPET_OPEN = "\x01"
SNIPPET_CLOSE = "\x02"


def sanitize_snippet(raw: str) -> str:
    escaped = html.escape(raw, quote=True)
    return escaped.replace(SNIPPET_OPEN, "<mark>").replace(SNIPPET_CLOSE, "</mark>")
```

### Auth — Dual Path

```python
# backend/src/auth/dependencies.py

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dual auth: BFF Proxy header (browser) or Bearer API key (CLI).
    """
    # 1. Check Authorization header for API key (CLI access)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer rw_"):
        key = auth_header.removeprefix("Bearer ")
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        user = await lookup_user_by_key_hash(db, key_hash)
        if user:
            return user
        raise HTTPException(401, "Invalid API key")

    # 2. Check BFF Proxy headers (Browser access)
    # The Next.js API route validates the NextAuth cookie and proxies the request
    # with a trusted X-User-Id header and a shared secret to prevent spoofing.
    proxy_secret = request.headers.get("X-Backend-Secret")
    user_id = request.headers.get("X-User-Id")
    
    if proxy_secret == settings.BACKEND_SECRET and user_id:
        user = await get_user_by_id(db, user_id)
        if user:
            return user

    raise HTTPException(401, "Authentication required")
```

### API Endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/api/ingest/sessions` | Batch metadata upload | API key |
| PUT | `/api/ingest/content/{session_key}/canonical` | Canonical content upload | API key |
| PUT | `/api/ingest/content/{session_key}/raw` | Raw content upload | API key |
| POST | `/api/ingest/content/{session_key}/raw/confirm` | Confirm raw upload completion | API key |
| POST | `/api/ingest/presign` | Generate presigned Blob upload URL | API key |
| GET | `/api/sessions` | List sessions (paginated, filtered) | BFF Proxy |
| GET | `/api/sessions/filters` | Distinct values for filters | BFF Proxy |
| GET | `/api/sessions/{id}` | Session detail | BFF Proxy |
| GET | `/api/sessions/{id}/content` | Session content from Blob | BFF Proxy |
| PATCH | `/api/sessions/{id}/star` | Toggle star | BFF Proxy |
| POST | `/api/sessions/{id}/trash` | Soft delete | BFF Proxy |
| DELETE | `/api/sessions/{id}/trash` | Restore from trash | BFF Proxy |
| POST | `/api/sessions/batch` | Batch operations | BFF Proxy |
| PUT | `/api/sessions/{id}/tags/{tag_id}` | Add tag to session | BFF Proxy |
| DELETE | `/api/sessions/{id}/tags/{tag_id}` | Remove tag from session | BFF Proxy |
| GET | `/api/search` | Full-text search | BFF Proxy |
| GET | `/api/stats` | Dashboard statistics | BFF Proxy |
| GET | `/api/tags` | List user's tags | BFF Proxy |
| POST | `/api/tags` | Create tag | BFF Proxy |
| PATCH | `/api/tags/{id}` | Update tag | BFF Proxy |
| DELETE | `/api/tags/{id}` | Delete tag | BFF Proxy |
| GET | `/api/projects` | List projects with aggregates | BFF Proxy |
| GET | `/api/projects/activity` | Project daily activity | BFF Proxy |
| GET | `/api/health` | Health check | None |

### CLI — Python Port

The reference CLI (`packages/cli`) should be ported to Python using **Typer**:

| Reference Command | Python Equivalent |
|-------------------|-------------------|
| Reference `login` | `rewind login` — open browser, start local callback server, save API key |
| Reference `sync` | `rewind sync` — discover, parse, upload, cursor rollback |
| Reference `status` | `rewind status` — show sync state, session counts |

Parser logic ports directly — the format knowledge (JSONL parsing, JSON schema, SQLite queries) is language-independent.

Key Python libraries for CLI:
- `typer` — CLI framework
- `httpx` — HTTP client with retry
- `rich` — console output formatting
- `platformdirs` — cross-platform config paths
- `watchfiles` — file system watcher (triggers re-scan only; does NOT replace inode+mtime+size identity check — see §Non-Negotiable Invariants)

### Testing Strategy & Validation Regimen

To ensure 100% feature and behavioral parity, testing must be disciplined and multi-layered.

#### Four-Layer Testing Regimen
1. **Layer 1: Unit Tests** (Focus: Core logic, chunking, deduplication)
   - Ensure specific test files map 1:1 to core helpers (`backend/src/core/chunking.py` → `test_chunking.py`).
2. **Layer 2: Integration Tests** (Focus: Database ops, API routes)
   - Use `testcontainers` or equivalent locally. Must verify PostgreSQL FTS triggers and `ts_headline` responses.
3. **Layer 3: E2E Browser Tests** (Focus: NextAuth, CLI BFF proxy, Replay UX)
   - Playwright to execute a full login → sync → view replay loop.
4. **Layer 4: Per-Source Manual E2E** (Focus: Parser behavioral parity)
   - Manual verification using real JSON/SQLite outputs from Claude, Gemini, OpenCode, Codex, and Copilot. Ensure no skipped messages, correct tool call parsing, and CRDT reconstruction.

| Layer | Tool | Coverage Target |
|-------|------|----------------|
| Python unit tests | pytest + pytest-asyncio | 90% |
| Python type check | mypy (strict) or pyright | Zero errors |
| Python lint | Ruff | Zero warnings |
| Frontend unit tests | Vitest | 90% |
| Frontend type check | tsc --noEmit | Zero errors |
| Frontend lint | ESLint | Zero warnings |
| Integration tests | pytest + testcontainers (PostgreSQL) | Key flows |
| E2E tests | Playwright (Phase 5) | Critical paths |

Adopt the reference project's practice of colocated test files (`*.test.ts` for frontend, `test_*.py` for backend).

---

## Non-Negotiable Invariants

> These constraints are hard requirements derived from the reference project's production experience. Violating any of them will cause data corruption, security vulnerabilities, or silent bugs. AI agents must treat these as non-negotiable.

### Ingest Protocol

| Invariant | Detail |
|-----------|--------|
| 4-field idempotency check | Every upsert must compare `content_hash`, `raw_hash`, `parser_revision`, AND `schema_version`. Using only `snapshot_at` allows stale parser output to overwrite newer data. |
| Content-Length required | Requests without `Content-Length` header must be rejected with HTTP `411 Length Required`. No exceptions. |
| Metadata size limit | Metadata batch POST body max: **2 MB**. Reject with `413`. |
| Content size limit | Content PUT body max: **50 MB** (compressed). Reject with `413`. |
| Gzip decompressed limit | Stream-track decompressed size; abort at **256 MB** with `413`. This is gzip bomb defense. |
| Batch size | Metadata batch POST: max **50 sessions** per request. |

### Blob Storage Keys

| Key Type | Format | Mutability |
|----------|--------|-----------|
| Canonical | `{user_id}/{session_key}/canonical.json.gz` | **Mutable** — overwritten on re-ingest |
| Raw | `{user_id}/{session_key}/raw/{raw_hash}.json.gz` | **Immutable** — content-addressed, never overwritten |

### FTS Safety

| Invariant | Detail |
|-----------|--------|
| Snippet sanitization | FTS snippets must use trusted delimiters (for example `\x01`/`\x02`), then HTML-escape the full snippet, then replace only those delimiters with `<mark>`/`</mark>`. Do not return raw `ts_headline` HTML directly. |
| Chunking: no truncation | Messages are split into ~2000-char chunks at paragraph boundaries. Content is **never truncated** — all chunks are indexed. |

### Auth Protocol

| Invariant | Detail |
|-----------|--------|
| Session issuer | NextAuth is the **sole session issuer**. Python backend never issues browser sessions. |
| BFF proxy pattern | **Required**: NextAuth v5 uses JWE by default, not plain JWS. Do not attempt to decrypt them in Python. Use the BFF proxy pattern where Next.js API routes resolve the session via `auth()` and pass `X-User-Id` and `X-Backend-Secret` to Python. |
| API key storage | Keys are generated once, shown to user once, stored as SHA-256 hash. Plaintext is **never** persisted server-side. |
| API key prefix | `rw_` — used for client-side identification and routing in dual-auth middleware. |
| Dev auth domain | CLI auth must use a real HTTPS dev domain, not localhost. Session cookies are domain-bound. |

### Parser Protocol & Edge Cases

| Invariant | Detail |
|-----------|--------|
| Dual output | Every parser must emit both `CanonicalSession` (normalized) AND `RawSessionArchive` (verbatim source). |
| Parse errors logged | Parse failures must be logged to a persistent error file, never silently dropped. |
| Cursor rollback | On upload failure, cursors must roll back so next sync re-processes failed sessions. |
| File change detection | Triple-check: inode + mtime + size. A file is "unchanged" only when ALL THREE match. |
| Claude Block Variants | Handle multiple block variants gracefully (e.g., `text`, `tool_use`, `tool_result`, `assistant_message`). Strip signatures if needed but preserve structural intent. |
| Gemini Skipped Messages | Gemini often interleaves system logs or skips messages in the UI. Ensure the parser indexes exactly what the local JSON files declare without choking on gaps in ordinals. |
| Copilot CRDT Protocol | VSCode Copilot stores conversations via an append-only CRDT. Parsers must fold these operations correctly to recreate the final conversation state. Never assume a flat linear log. |

### Next.js & NextAuth Pitfalls

| Invariant | Detail |
|-----------|--------|
| No `204 No Content` Bodies | Never attach a body to an HTTP `204` response in Next.js. Next.js App Router will silently crash or throw uncatchable errors if a 204 response has a body. Use `200 OK` with `{}` or `204` with NO body. |
| Avoid Nested `@auth/core` versions | NextAuth v5 (Beta) is highly sensitive to dependency mismatches. Ensure you are not installing multiple conflicting versions of `@auth/core` alongside `next-auth@beta`. |

---

## Environment Variables Checklist

> Complete reference of all environment variables needed across the stack. This section is self-contained so AI agents can configure any component without cross-referencing other files.

### Frontend (Next.js)

| Variable | Example Value | When Needed | Source |
|----------|--------------|-------------|--------|
| `NEXTAUTH_URL` | `https://rewind.dev.example.com` (dev), `https://app.example.com` (prod) | Phase 1 | **Must be a real HTTPS domain, not localhost** — session cookies are bound to the domain |
| `AUTH_SECRET` | `openssl rand -base64 32` output | Phase 1 | Generate once for NextAuth; frontend runtime and frontend deploys must use the same value |
| `AUTH_GOOGLE_ID` | `123456789.apps.googleusercontent.com` | Phase 1 | Google Cloud Console → OAuth 2.0 credentials |
| `AUTH_GOOGLE_SECRET` | `GOCSPX-...` | Phase 1 | Google Cloud Console → OAuth 2.0 credentials |
| `BACKEND_URL` | `http://localhost:8000` (dev), `https://api.example.com` (prod) | Phase 1 | Your backend deployment URL |
| `NEXT_PUBLIC_APP_NAME` | `Rewind` | Phase 3 | Product name |

### Backend (FastAPI)

| Variable | Example Value | When Needed | Source |
|----------|--------------|-------------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost:5432/rewind` | Phase 0 | docker-compose (dev) or Azure PostgreSQL (prod) |
| `BACKEND_SECRET` | `openssl rand -base64 32` output | Phase 1 | Used by Next.js to authenticate BFF proxy requests to Python API |
| `AZURE_STORAGE_CONNECTION_STRING` | `DefaultEndpointsProtocol=https;AccountName=...` | Phase 2 | Azurite (dev) or Azure Portal (prod) |
| `AZURE_STORAGE_CONTAINER_NAME` | `sessions` | Phase 2 | Created in Blob Storage account |
| `CORS_ORIGINS` | `https://rewind.dev.example.com` (dev), `https://app.example.com` (prod) | Phase 1 | Your frontend URL(s), comma-separated — must match `NEXTAUTH_URL` domain |
| `API_RATE_LIMIT` | `100/minute` | Phase 5 | Tuning decision |
| `MAX_CONTENT_SIZE_BYTES` | `52428800` (50MB) | Phase 2 | Security — matches reference limit |
| `MAX_DECOMPRESSED_SIZE_BYTES` | `268435456` (256MB) | Phase 2 | Security — gzip bomb defense |
| `LOG_LEVEL` | `INFO` | Phase 0 | `DEBUG` for dev, `INFO` for prod |

### CLI

| Variable | Example Value | When Needed | Source |
|----------|--------------|-------------|--------|
| `REWIND_API_URL` | `https://api.example.com` | Phase 1 | Backend URL; saved in `~/.config/rewind/config.json` on login |
| `REWIND_API_KEY` | `rw_...` | Phase 1 | Generated on login; saved in `~/.config/rewind/config.json` |

### Local Development (docker-compose)

| Variable | Example Value | When Needed | Source |
|----------|--------------|-------------|--------|
| `POSTGRES_USER` | `rewind` | Phase 0 | docker-compose.yml |
| `POSTGRES_PASSWORD` | `devpassword` | Phase 0 | docker-compose.yml |
| `POSTGRES_DB` | `rewind` | Phase 0 | docker-compose.yml |
| `AZURITE_ACCOUNT_NAME` | `devstoreaccount1` | Phase 2 | Azurite default |
| `AZURITE_ACCOUNT_KEY` | (Azurite default key) | Phase 2 | Azurite default |

### CI/CD (GitHub Actions Secrets)

| Secret | When Needed | Source |
|--------|-------------|--------|
| `AZURE_CREDENTIALS` | Phase 5 | Azure service principal JSON |
| `AZURE_SUBSCRIPTION_ID` | Phase 5 | Azure Portal |
| `REGISTRY_LOGIN_SERVER` | Phase 5 | Azure Container Registry URL (if using ACR) |
| `AUTH_SECRET` | Phase 5 | Same value as frontend runtime |
| `BACKEND_SECRET` | Phase 5 | Shared secret between Next.js BFF routes and Python backend |
| `AUTH_GOOGLE_ID` | Phase 5 | Google Cloud Console |
| `AUTH_GOOGLE_SECRET` | Phase 5 | Google Cloud Console |
| `DATABASE_URL` | Phase 5 | Azure PostgreSQL connection string |
| `AZURE_STORAGE_CONNECTION_STRING` | Phase 5 | Azure Blob Storage connection string |

> **Critical**: `AUTH_SECRET` must be identical anywhere NextAuth runs, and `BACKEND_SECRET` must be identical between the Next.js BFF layer and the Python backend. Store both in Azure Key Vault for production.
