# New Project Blueprint — Index

> Generated from a reference repository (architecture study only).
> These documents describe a **new project** to be built in a separate repository.
> The reference repo is studied for architecture ideas, not modified.

## Critical Constraints — Read Before Any Phase

These three constraints are the most common source of implementation bugs. Violating any of them will cause auth failures, data corruption, or architectural drift that is expensive to fix later.

1. **Dev auth requires a real HTTPS domain, not localhost.** Session cookies are bound to the domain. If the CLI opens `http://localhost:3000/api/auth/cli`, `auth()` returns null. Use a reverse proxy (Caddy + mkcert) with a real dev domain like `https://rewind.dev.example.com`. See **03** §Auth — Modify Slightly.

2. **Auth source of truth: NextAuth only.** NextAuth issues all sessions (browser) and the CLI auth callback lives in Next.js. The Python backend **validates** API key hashes and trusts the BFF proxy for browser sessions — it never issues sessions. Do not implement an OAuth adapter in Python. **⚠ Use the BFF proxy pattern for browser auth:** NextAuth v5 uses JWE (encrypted tokens) by default, making Python decryption brittle. Instead, Next.js API routes must resolve the session via `auth()` and proxy requests to the Python backend with a trusted `X-User-Id` header and shared secret. See **03** §Auth — Modify Slightly.

3. **Ingest has non-negotiable protocol invariants.** The 4-field idempotency check (`content_hash`, `raw_hash`, `parser_revision`, `schema_version`), size limits (50MB content, 2MB metadata, 256MB decompressed), `Content-Length` required (411 on missing), and FTS snippet sanitization are not optional. See **03** §Non-Negotiable Invariants.

## Locked Decisions

These are no longer `Pending Confirmation` — they have been decided:

| Decision | Value |
|----------|-------|
| Product name | **Rewind** |
| CLI command | `rewind` |
| PyPI package | `rewind` |
| API key prefix | `rw_` |
| Database | PostgreSQL (Azure Flexible Server) |
| CLI language | Python (Typer) |
| Backend hosting (V1) | Azure App Service |
| Auth issuer | NextAuth (sole issuer) |
| Reference license | MIT — confirmed |

## Documents

| # | File | Contents |
|---|------|----------|
| 00 | [00-index.md](./00-index.md) | This index |
| 01 | [01-reference-analysis.md](./01-reference-analysis.md) | Reference project overview, architecture breakdown, development workflow, git history interpretation |
| 02 | [02-new-project-prd.md](./02-new-project-prd.md) | New project definition, reference reuse strategy, PRD outline |
| 03 | [03-architecture-blueprint.md](./03-architecture-blueprint.md) | Architecture blueprint with **Frontend Reference** and **Python Backend Blueprint** subsections, recommended repo structure |
| 04 | [04-azure-and-implementation.md](./04-azure-and-implementation.md) | Azure infrastructure mapping, staged implementation plan (7 phases: Phase 0 to 6) |
| 05 | [05-launch-and-risks.md](./05-launch-and-risks.md) | Manual user actions, launch blockers and risks, pending confirmations |

## How to Use

1. Read **01** to understand what the reference project does and how it works.
2. Read **02** to see the new project's product definition and scope.
3. Read **03** for the technical architecture — this is where the frontend-vs-backend split is explicit.
4. Read **04** for the Azure mapping and a phased build plan you can hand to an AI agent.
5. Read **05** before starting: it lists everything that requires human action and things that could block launch.

## AI Agent Usage Guide

When handing these documents to an AI agent for implementation, **do not load all files at once**. Feed only the files relevant to the current phase. This keeps context focused and prevents the agent from being overwhelmed.

| Phase | Load These Files | Purpose |
|-------|-----------------|---------|
| Phase 0: Discovery & Setup | **03** + **04** (Phase 0 section) + **05** (Quick Reference) | Repo structure, docker-compose, CI, pre-flight manual actions |
| Phase 1: Auth & Core Types | **03** (Architecture Blueprint, Python Backend: Auth + Schema sections) + **04** (Phase 1 section) | Data model, auth implementation, CLI login |
| Phase 2: Parsers & Ingest | **03** (Python Backend: Ingest + Search + Blob sections) + **04** (Phase 2 section) + **01** (Section 2 for reference architecture context) | Parsers, upload pipeline, ingest API, FTS |
| Phase 3: Dashboard & Search | **03** (Frontend Reference section) + **04** (Phase 3 section) | Frontend pages, layout, component patterns, API client |
| Phase 4: Organization & Polish | **03** (Frontend Reference: Component Patterns) + **04** (Phase 4 section) | Tags, stars, trash, bulk ops, projects |
| Phase 5: Deployment & Hardening | **04** (Azure Mapping + Phase 5 section) + **05** (full file) | Azure provisioning, Docker, CI/CD, security, manual actions |
| Phase 6: Expansion | **04** (Phase 6 section) + **01** (reference parser details) | Remaining parsers, E2E, advanced features |

Each phase section in **04** includes a `Required Context` field that lists exactly which sections from other files the agent needs.

## Conventions

- `Confirmed` — derived directly from reference project source code
- `Inferred` — reasonable assumption based on patterns observed
- `Pending Confirmation` — requires a decision from the project owner before proceeding
- `Manual Action Required` — cannot be automated; human must perform this step
- `Launch Blocking` — must be resolved before production deployment
