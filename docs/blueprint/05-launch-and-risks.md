# 05 — Launch, Risks & Pending Confirmations

## 11. Manual User Actions

These items **cannot be automated by AI** and require human intervention.

### Azure Setup (`Launch Blocking`)

| Action | When Needed | Blocking? |
|--------|------------|-----------|
| Create Azure subscription (or use existing) | Phase 0 | `Launch Blocking` |
| Set up billing/payment method | Phase 0 | `Launch Blocking` |
| Choose Azure region | Phase 0 | `Launch Blocking` |
| Provision Azure Database for PostgreSQL Flexible Server | Phase 5 (or Phase 0 for early testing) | `Launch Blocking` |
| Provision Azure Blob Storage account + create containers | Phase 5 | `Launch Blocking` |
| Provision Azure App Service plans (frontend + backend) | Phase 5 | `Launch Blocking` |
| Provision Azure Key Vault and store secrets | Phase 5 | `Launch Blocking` |
| Set up Azure Application Insights | Phase 5 | Recommended but not blocking |

> **Note**: Phase 0–4 can run entirely on local Docker (PostgreSQL + Azurite). Azure provisioning can be deferred to Phase 5, but decisions about region and SKU should be made earlier.

### Authentication Setup (`Launch Blocking`)

| Action | When Needed | Blocking? |
|--------|------------|-----------|
| Create Google Cloud project (or use existing) | Phase 1 | `Launch Blocking` |
| Enable Google OAuth API | Phase 1 | `Launch Blocking` |
| Create OAuth 2.0 credentials (client ID + secret) | Phase 1 | `Launch Blocking` |
| Configure OAuth consent screen (scopes, domain) | Phase 1 | `Launch Blocking` |
| Add authorized redirect URIs for dev and prod | Phase 1 (dev), Phase 5 (prod) | `Launch Blocking` |
| Generate `AUTH_SECRET` for NextAuth JWT signing | Phase 1 | `Launch Blocking` |

### Domain & DNS (`Launch Blocking` for Production)

| Action | When Needed | Blocking? |
|--------|------------|-----------|
| Choose and register domain name | Phase 0 (decision), Phase 5 (action) | `Launch Blocking` for prod |
| Configure DNS records (A/CNAME → Azure App Service) | Phase 5 | `Launch Blocking` for prod |
| Set up TLS certificate (Azure-managed or custom) | Phase 5 | `Launch Blocking` for prod |
| Configure CORS allowed origins with production domain | Phase 5 | `Launch Blocking` |

### Repository & CI/CD

| Action | When Needed | Blocking? |
|--------|------------|-----------|
| Create new Git repository | Phase 0 | `Launch Blocking` |
| Configure GitHub repository settings (branch protection, etc.) | Phase 0 | Recommended |
| Set up GitHub Actions secrets (Azure credentials, OAuth secrets) | Phase 5 | `Launch Blocking` for CI/CD |
| Create PyPI account for CLI distribution | Phase 6 | Not blocking for launch |
| Create Azure service principal (or configure GitHub OIDC) | Phase 5 | `Launch Blocking` for CI/CD |
| Assign Contributor role on Azure subscription to service principal | Phase 5 | `Launch Blocking` for CI/CD |
| Configure federated credential (if using GitHub OIDC) | Phase 5 | Recommended over service principal secret |

### Branding & Content

| Action | When Needed | Blocking? |
|--------|------------|-----------|
| ~~Choose product name~~ | ~~Phase 0~~ | **Decided** — "Rewind" |
| Design logo and visual identity | Phase 3 | Recommended before launch |
| Write landing page content | Phase 3 | Recommended before launch |
| Choose primary brand color(s) | Phase 3 | Recommended |

---

## 12. Launch Blockers And Risks

### Critical Blockers

| Blocker | Category | Mitigation |
|---------|----------|-----------|
| No Azure subscription | Infrastructure | Must be provisioned manually before Phase 5 |
| No Google OAuth credentials | Auth | Must be created in Google Cloud Console |
| No domain name | DNS | Can use `*.azurewebsites.net` for MVP, but real domain needed for production |
| No `AUTH_SECRET` / `BACKEND_SECRET` | Security | Generate with `openssl rand -base64 32`; `AUTH_SECRET` for NextAuth, `BACKEND_SECRET` shared between frontend proxy and Python backend |
| PostgreSQL not provisioned | Database | Use local Docker until Phase 5; must provision for prod |
| Blob Storage not provisioned | Storage | Use local Azurite until Phase 5; must provision for prod |

### High-Risk Areas

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Parser correctness bugs | High | Medium | Port reference test cases; test against real local data early |
| Ingest idempotency bugs | Medium | High | The reference project iterated this logic 13+ times; copy the decision tree exactly |
| FTS quality (PG vs SQLite FTS5) | Medium | Medium | PostgreSQL tsvector is different from FTS5; may need query tuning |
| BFF proxy header spoofing | Low | High | Ensure frontend and backend share a strong secret to authenticate proxy requests |
| First deployment issues | High | Medium | The reference had ~20 deployment fixes; budget time for debugging |
| Cold start latency on App Service B1 | Medium | Low | Consider Always On setting ($) or accept for MVP |
| Gzip bomb attack on ingest | Low | High | Port reference defenses (256MB limit, streaming size tracking) |
| Large session handling (5MB+) | Medium | Medium | PostgreSQL handles large rows better than D1, but test with real data |

### Medium-Risk Areas

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Python async complexity | Medium | Medium | Use FastAPI's native async; follow established patterns |
| SQLAlchemy migration conflicts | Low | Medium | Use Alembic with proper branching strategy |
| Frontend-backend API contract drift | Medium | Medium | Use OpenAPI schema from FastAPI; generate TS types |
| CORS misconfiguration | Medium | Low | Test cross-origin requests in dev before deploying |
| Concurrent upload race conditions | Low | High | Port reference's `content_hash` idempotency check |
| DB connection pool exhaustion | Medium | Medium | Configure asyncpg pool size; monitor in Application Insights |

### Compliance & Legal

| Item | Status | Action Required |
|------|--------|----------------|
| Reference project license | `Confirmed` — MIT license | Preserve attribution and LICENSE notice in new project |
| User data privacy (GDPR, etc.) | `Pending Confirmation` | Determine if users are in EU; add data deletion flow |
| Google OAuth terms of service | `Confirmed` — standard use | No special action beyond consent screen |
| PyPI package name availability | `Pending Confirmation` | Check if desired CLI package name is available |
| Session content sensitivity | `Inferred` — conversations may contain secrets | Add documentation warning users about sensitive data in AI sessions |

---

## 13. Pending Confirmations

These items require decisions from the project owner. The table below shows which have safe defaults and which must be decided before a specific phase.

### Product Decisions

| Item | Options | Default | Safe Default? | Must Decide Before |
|------|---------|---------|--------------|-------------------|
| ~~Product name~~ | ~~(your choice)~~ | **Rewind** | **Decided** | Phase 0 |
| Branding colors / visual identity | (your choice) | Neutral/blue palette | Yes | Phase 3 |
| Landing page content and positioning | (your choice) | Developer-focused, minimal | Yes | Phase 3 |
| ~~CLI package name (PyPI)~~ | ~~(your choice)~~ | **`rewind`** | **Decided** | Phase 6 |

### Technical Decisions

| Item | Options | Default | Safe Default? | Must Decide Before |
|------|---------|---------|--------------|-------------------|
| CLI language | ~~Python vs Node.js~~ | Python (Typer) | **Decided** | Phase 0 |
| Database | ~~PostgreSQL vs Azure SQL~~ | PostgreSQL (Flexible Server) | **Decided** | Phase 0 |
| Backend hosting | ~~App Service vs Container Apps~~ | Azure App Service | **Decided** | Phase 5 |
| Frontend hosting | Same App Service vs separate | Separate App Service | Yes | Phase 5 |
| IaC tool | Bicep vs Terraform | Bicep (Azure-native) | Yes | Phase 5 |
| FTS engine | PostgreSQL tsvector vs Azure AI Search | PostgreSQL tsvector | Yes | Phase 2 |
| Auth providers beyond Google | GitHub, Azure AD, others? | Google only for V1 | Yes | Phase 6 |

### Infrastructure Decisions

| Item | Options | Default | Safe Default? | Must Decide Before |
|------|---------|---------|--------------|-------------------|
| Azure region | (depends on user location) | East US 2 | Yes | Phase 0 |
| Azure subscription | New vs existing | Existing or new | **No** — must confirm | Phase 0 |
| Production PostgreSQL SKU | Burstable B1ms ($13) vs GP D2ds ($100) | Burstable B1ms for MVP | Yes | Phase 5 |
| Custom domain | (your choice) | `*.azurewebsites.net` for MVP | Yes | Phase 5 |
| CDN | Azure Front Door vs none | None for MVP | Yes | Phase 6 |
| Monitoring level | Basic (Application Insights) vs full (Azure Monitor) | Basic for MVP | Yes | Phase 5 |

### Operational Decisions

| Item | Options | Default | Safe Default? | Must Decide Before |
|------|---------|---------|--------------|-------------------|
| Expected traffic level | < 100 users, < 1000, < 10000 | < 100 (single developer / small team) | Yes | Phase 5 |
| Data retention policy | Keep forever vs TTL | Keep forever | Yes | Phase 6 |
| Backup strategy | Azure automatic vs manual | Azure automatic (PostgreSQL) | Yes | Phase 5 |
| On-call / alerting | Email vs PagerDuty vs none | Email alerts via Azure Monitor | Yes | Phase 5 |
| Compliance needs (GDPR, SOC2, etc.) | Required vs not | Not required for MVP | Yes | Phase 6 |

---

## Manual Actions by Phase

> Quick-reference view grouping all manual actions by the phase in which they are needed. AI agents should check this section when starting a new phase.

### Phase 0 — Before You Write Any Code

- [ ] Confirm product name: **Rewind** (locked decision — see `00-index.md` §Locked Decisions)
- [ ] Create a new Git repository
- [ ] CLI language: **Python (Typer)** (locked decision — no need to decide)
- [ ] Create or confirm Azure subscription
- [ ] Set up Azure billing/payment method
- [ ] Choose Azure region (default: East US 2)
- [ ] Configure GitHub repository settings (branch protection — recommended)

### Phase 1 — Auth Setup

- [ ] Create or select a Google Cloud project
- [ ] Enable Google OAuth API in Google Cloud Console
- [ ] Create OAuth 2.0 credentials (client ID + secret)
- [ ] Configure OAuth consent screen (scopes, test users)
- [ ] Add authorized redirect URIs for dev (`https://rewind.dev.example.com/api/auth/callback/google` — must be a real HTTPS domain, not localhost)
- [ ] Generate `AUTH_SECRET` with `openssl rand -base64 32`

### Phase 3 — Branding Decisions

- [ ] Choose primary brand color(s)
- [ ] Design logo and visual identity (recommended)
- [ ] Write landing page content (recommended)

### Phase 5 — Azure Provisioning & Production

- [ ] Provision Azure Database for PostgreSQL Flexible Server
- [ ] Provision Azure Blob Storage account + create `sessions` container
- [ ] Provision Azure App Service plans (frontend + backend)
- [ ] Provision Azure Key Vault and store secrets (`AUTH_SECRET`, DB connection string, Blob connection string, OAuth secrets)
- [ ] Set up Azure Application Insights (recommended)
- [ ] Choose and register domain name
- [ ] Configure DNS records (A/CNAME → Azure App Service)
- [ ] Set up TLS certificate (Azure-managed or custom)
- [ ] Configure CORS allowed origins with production domain
- [ ] Add authorized redirect URIs for prod in Google Cloud Console
- [ ] Set up GitHub Actions secrets (Azure credentials, OAuth secrets, DB URL, Blob connection string)
- [ ] Create Azure service principal or configure GitHub OIDC federation
- [ ] Assign Contributor role on Azure subscription to the deploy identity

### Phase 6 — Distribution

- [ ] Check PyPI package name availability for CLI
- [ ] Create PyPI account for CLI distribution
- [ ] Review reference project license for derivative work permissions

---

## Quick Reference: What to Do First

Before starting Phase 0, resolve these minimum items:

1. **Confirm product name** ("Rewind" — already locked)
2. **Create a new Git repository**
3. **CLI language is Python** (already locked — no decision needed)
4. **Have a Google Cloud project** (for OAuth — can use an existing one)
5. **Have an Azure subscription** (can be free tier for dev)

Everything else can be decided as you go.
