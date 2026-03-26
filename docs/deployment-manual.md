# Rewind — Production Deployment Manual

> Step-by-step guide to deploy the Rewind platform from zero to production on Azure.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Azure Subscription & CLI Setup](#2-azure-subscription--cli-setup)
3. [Google OAuth Credentials](#3-google-oauth-credentials)
4. [Generate Secrets](#4-generate-secrets)
5. [Provision Azure Infrastructure (Bicep)](#5-provision-azure-infrastructure-bicep)
6. [Configure the Database](#6-configure-the-database)
7. [Populate Key Vault Secrets](#7-populate-key-vault-secrets)
8. [Configure GitHub Repository](#8-configure-github-repository)
9. [First Deployment](#9-first-deployment)
10. [Verify Deployment](#10-verify-deployment)
11. [Custom Domain & TLS (Optional)](#11-custom-domain--tls-optional)
12. [Frontend Auth Setup (NextAuth)](#12-frontend-auth-setup-nextauth)
13. [CLI Setup & First Sync](#13-cli-setup--first-sync)
14. [Monitoring & Alerts](#14-monitoring--alerts)
15. [Maintenance & Operations](#15-maintenance--operations)
16. [Troubleshooting](#16-troubleshooting)
17. [Appendix: Environment Variables Reference](#appendix-environment-variables-reference)

---

## 1. Prerequisites

Before starting, ensure you have:

- [ ] An **Azure account** with an active subscription ([create one free](https://azure.microsoft.com/free/))
- [ ] **Azure CLI** installed (`az --version` >= 2.50) — [Install guide](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [ ] **Bicep CLI** installed (bundled with Azure CLI >= 2.20)
- [ ] A **GitHub account** with the Rewind repository pushed
- [ ] A **Google Cloud account** (for OAuth credentials)
- [ ] **Docker** installed locally (for building/testing images)
- [ ] **Python 3.9+** and **Node.js 20+** installed locally (for development)

---

## 2. Azure Subscription & CLI Setup

### 2.1 Login to Azure

```bash
az login
```

### 2.2 Set your default subscription

```bash
# List subscriptions
az account list --output table

# Set the one you want to use
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"
```

### 2.3 Register required resource providers

```bash
az provider register --namespace Microsoft.Web
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Insights
```

### 2.4 Create a resource group

```bash
az group create --name rg-rewind-prod --location eastus
```

> **Tip:** Use `eastus` or `eastus2` for lowest latency to US users. Replace with your preferred region.

---

## 3. Google OAuth Credentials

### 3.1 Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Rewind Auth")
3. Note the **Project ID**

### 3.2 Enable the OAuth API

1. Navigate to **APIs & Services > Library**
2. Search for "Google Identity" or "Google+ API"
3. Enable it (if not already)

### 3.3 Configure the OAuth consent screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** (unless you have a Google Workspace org)
3. Fill in:
   - App name: `Rewind`
   - User support email: your email
   - Developer contact: your email
4. Scopes: add `openid`, `email`, `profile`
5. Test users: add your email (required while in testing mode)

### 3.4 Create OAuth 2.0 credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Name: `Rewind Web`
5. Authorized redirect URIs:
   - For development: `http://localhost:3000/api/auth/callback/google`
   - For production: `https://<YOUR_DOMAIN>/api/auth/callback/google`
6. Note the **Client ID** and **Client Secret**

> **Important:** If you don't have a custom domain yet, you'll use the Azure App Service hostname:
> `https://<frontend-app-name>.azurewebsites.net/api/auth/callback/google`

---

## 4. Generate Secrets

Generate the required secrets on your local machine:

```bash
# AUTH_SECRET — used by NextAuth to encrypt JWT tokens
openssl rand -base64 32
# Save the output → AUTH_SECRET

# BACKEND_SECRET — shared secret between Next.js BFF proxy and FastAPI
openssl rand -base64 32
# Save the output → BACKEND_SECRET

# PostgreSQL admin password — use a strong password
openssl rand -base64 24
# Save the output → POSTGRES_ADMIN_PASSWORD
```

Keep all three values safe — you'll need them in the next steps.

---

## 5. Provision Azure Infrastructure (Bicep)

### 5.1 Deploy to the resource group

```bash
cd infra/

# For production
az deployment group create \
  --resource-group rg-rewind-prod \
  --template-file main.bicep \
  --parameters @parameters/prod.bicepparam \
  --parameters postgresAdminPassword='<YOUR_POSTGRES_PASSWORD>'
```

> For a dev/staging environment, use `@parameters/dev.bicepparam` and a different resource group.

### 5.2 Note the deployment outputs

```bash
az deployment group show \
  --resource-group rg-rewind-prod \
  --name main \
  --query properties.outputs \
  --output json
```

Record these values:
- `backendHostname` — e.g., `app-backend-rewind-prod.azurewebsites.net`
- `frontendHostname` — e.g., `app-frontend-rewind-prod.azurewebsites.net`
- `postgresServerFqdn` — e.g., `pg-rewind-prod.postgres.database.azure.com`
- `storageAccountName` — e.g., `strewindprod`
- `keyVaultUri` — e.g., `https://kv-rewind-prod.vault.azure.net/`
- `appInsightsInstrumentationKey`

---

## 6. Configure the Database

### 6.1 Create the application database

The Bicep template creates the PostgreSQL server but not the application database. Create it:

```bash
az postgres flexible-server db create \
  --resource-group rg-rewind-prod \
  --server-name pg-rewind-prod \
  --database-name rewind
```

### 6.2 Allow your local IP (for direct access)

```bash
# Get your public IP
MY_IP=$(curl -s ifconfig.me)

az postgres flexible-server firewall-rule create \
  --resource-group rg-rewind-prod \
  --name pg-rewind-prod \
  --rule-name allow-my-ip \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP
```

### 6.3 Build the connection string

```
postgresql+asyncpg://rewindadmin:<YOUR_POSTGRES_PASSWORD>@pg-rewind-prod.postgres.database.azure.com:5432/rewind?sslmode=require
```

---

## 7. Populate Key Vault Secrets

The Bicep deployment created 6 placeholder secrets with value `REPLACE_ME`. Replace them with real values:

```bash
VAULT_NAME="kv-rewind-prod"

# 1. Database URL
az keyvault secret set --vault-name $VAULT_NAME \
  --name "DATABASE-URL" \
  --value "postgresql+asyncpg://rewindadmin:<POSTGRES_PASSWORD>@pg-rewind-prod.postgres.database.azure.com:5432/rewind?sslmode=require"

# 2. Azure Storage connection string
STORAGE_CONN=$(az storage account show-connection-string \
  --resource-group rg-rewind-prod \
  --name strewindprod \
  --query connectionString -o tsv)

az keyvault secret set --vault-name $VAULT_NAME \
  --name "AZURE-STORAGE-CONNECTION-STRING" \
  --value "$STORAGE_CONN"

# 3. Backend secret (shared between Next.js and FastAPI)
az keyvault secret set --vault-name $VAULT_NAME \
  --name "BACKEND-SECRET" \
  --value "<YOUR_BACKEND_SECRET>"

# 4. Auth secret (NextAuth JWT encryption)
az keyvault secret set --vault-name $VAULT_NAME \
  --name "AUTH-SECRET" \
  --value "<YOUR_AUTH_SECRET>"

# 5. Google OAuth Client ID
az keyvault secret set --vault-name $VAULT_NAME \
  --name "AUTH-GOOGLE-ID" \
  --value "<YOUR_GOOGLE_CLIENT_ID>"

# 6. Google OAuth Client Secret
az keyvault secret set --vault-name $VAULT_NAME \
  --name "AUTH-GOOGLE-SECRET" \
  --value "<YOUR_GOOGLE_CLIENT_SECRET>"
```

### 7.1 Verify secrets are set

```bash
az keyvault secret list --vault-name $VAULT_NAME --output table
```

---

## 8. Configure GitHub Repository

### 8.1 Create an Azure service principal for CI/CD

```bash
az ad sp create-for-rbac \
  --name "sp-rewind-deploy" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/rg-rewind-prod \
  --json-auth
```

Copy the entire JSON output — this is your `AZURE_CREDENTIALS` secret.

### 8.2 Set GitHub Secrets and Variables

Go to your GitHub repository **Settings > Secrets and variables > Actions**.

**Secrets:**

| Name | Value |
|------|-------|
| `AZURE_CREDENTIALS` | The full JSON from `az ad sp create-for-rbac` |

**Variables:**

| Name | Value |
|------|-------|
| `BACKEND_APP_NAME` | `app-backend-rewind-prod` |
| `FRONTEND_APP_NAME` | `app-frontend-rewind-prod` |
| `RESOURCE_GROUP` | `rg-rewind-prod` |

### 8.3 Create the `production` environment

1. Go to **Settings > Environments**
2. Click **New environment** > name it `production`
3. (Optional) Add required reviewers or branch protection rules

### 8.4 Enable GHCR (GitHub Container Registry)

Ensure your repository has **Packages** write permission:
1. Go to **Settings > Actions > General**
2. Under **Workflow permissions**, select **Read and write permissions**

---

## 9. First Deployment

### 9.1 Trigger the deploy workflow

Push to the `main` branch or manually trigger the workflow:

```bash
git push origin main
```

The `deploy.yml` workflow will:
1. Build backend Docker image → push to GHCR
2. Build frontend Docker image → push to GHCR
3. Deploy both images to Azure App Service
4. Run Alembic migrations
5. Perform a health check smoke test

### 9.2 Monitor the deployment

Go to **Actions** tab in GitHub to watch the workflow progress.

### 9.3 Manual migration (if CI migration fails)

If the automated migration step fails, run it manually:

```bash
# SSH into the backend App Service
az webapp ssh --name app-backend-rewind-prod --resource-group rg-rewind-prod

# Inside the container:
cd /app
alembic upgrade head
```

---

## 10. Verify Deployment

### 10.1 Health check

```bash
curl https://app-backend-rewind-prod.azurewebsites.net/api/health
```

Expected response:
```json
{"status": "healthy", "database": "connected"}
```

### 10.2 Frontend

Open in browser:
```
https://app-frontend-rewind-prod.azurewebsites.net
```

You should see the Rewind dashboard (note: currently no auth, so it's publicly accessible).

### 10.3 Test the API

```bash
# List sessions (should return empty)
curl https://app-backend-rewind-prod.azurewebsites.net/api/sessions
```

---

## 11. Custom Domain & TLS (Optional)

### 11.1 Add a custom domain to the frontend App Service

```bash
# Add the custom domain
az webapp config hostname add \
  --webapp-name app-frontend-rewind-prod \
  --resource-group rg-rewind-prod \
  --hostname rewind.yourdomain.com

# Create a managed TLS certificate
az webapp config ssl create \
  --name app-frontend-rewind-prod \
  --resource-group rg-rewind-prod \
  --hostname rewind.yourdomain.com

# Bind the certificate
az webapp config ssl bind \
  --name app-frontend-rewind-prod \
  --resource-group rg-rewind-prod \
  --certificate-thumbprint <THUMBPRINT> \
  --ssl-type SNI
```

### 11.2 DNS configuration

Add these DNS records at your domain registrar:

| Type | Name | Value |
|------|------|-------|
| CNAME | `rewind` | `app-frontend-rewind-prod.azurewebsites.net` |
| TXT | `asuid.rewind` | (Azure domain verification token, shown in portal) |

For the backend API (if separate subdomain):

| Type | Name | Value |
|------|------|-------|
| CNAME | `api.rewind` | `app-backend-rewind-prod.azurewebsites.net` |

### 11.3 Update CORS and auth redirect URIs

After setting up custom domains, update:

1. **Backend CORS**: Add your custom domain to `CORS_ORIGINS` in the App Service configuration
2. **Google OAuth**: Add the new redirect URI to the Google Cloud Console
3. **NextAuth URL**: Update `NEXTAUTH_URL` in the frontend App Service configuration

---

## 12. Frontend Auth Setup (NextAuth)

> **Note:** As of the current codebase, NextAuth is NOT implemented in the frontend. This section documents what needs to be implemented before production use.

### 12.1 What's needed

The following must be implemented in the frontend before the app can be used in production with authentication:

1. Install `next-auth` (or `@auth/nextjs` v5) dependency
2. Create `src/app/api/auth/[...nextauth]/route.ts` with Google provider
3. Create `src/middleware.ts` to protect `/dashboard/**` routes
4. Add `SessionProvider` to root layout
5. Create BFF proxy API routes (`src/app/api/sessions/route.ts`, etc.) that:
   - Resolve the user session via `auth()`
   - Forward requests to the Python backend with `X-User-Id` and `X-Backend-Secret` headers
6. Update `api.ts` to call the BFF proxy routes instead of the backend directly
7. Create a login page at `src/app/login/page.tsx`

### 12.2 Required environment variables for NextAuth

Set these on the frontend App Service (or in `packages/web/.env.local` for local dev):

| Variable | Value |
|------|-------|
| `NEXTAUTH_URL` | `https://rewind.yourdomain.com` (or Azure hostname) |
| `AUTH_SECRET` | (generated in step 4) |
| `AUTH_GOOGLE_ID` | (from Google Cloud Console) |
| `AUTH_GOOGLE_SECRET` | (from Google Cloud Console) |
| `BACKEND_URL` | `https://app-backend-rewind-prod.azurewebsites.net` |
| `BACKEND_SECRET` | (same as backend's `BACKEND_SECRET`) |

---

## 13. CLI Setup & First Sync

### 13.1 Install the CLI

```bash
cd cli/
pip install -e .
```

> **Known issue:** You may need to also `pip install pydantic` — it is currently missing from `pyproject.toml` dependencies.

### 13.2 Login

```bash
rewind login
```

This will prompt for:
- **API URL**: Enter your backend URL (e.g., `https://app-backend-rewind-prod.azurewebsites.net`)
- **API Key**: You'll need to generate an API key. Currently, there is no UI for this. You'll need to create one via the database:

```sql
-- Connect to the production database and run:
INSERT INTO users (id, name, email) VALUES (gen_random_uuid(), 'Your Name', 'your@email.com');

-- Then use the API to generate a key, or insert directly:
-- (The CLI login command validates rw_ prefix, so generate with the backend utility)
```

> **Note:** In the future, the web dashboard will have a Settings page for generating API keys.

### 13.3 Sync sessions

```bash
# Dry run first to see what would be synced
rewind sync --dry-run

# Sync all sources
rewind sync

# Sync a specific source only
rewind sync --source claude
```

### 13.4 Check status

```bash
rewind status
```

---

## 14. Monitoring & Alerts

### 14.1 Access Application Insights

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your resource group (`rg-rewind-prod`)
3. Click on the Application Insights resource (`ai-rewind-prod`)
4. Use **Live Metrics** for real-time monitoring
5. Use **Failures** to track error rates
6. Use **Performance** for latency analysis

### 14.2 Configure basic alerts

```bash
RG="rg-rewind-prod"
AI_NAME="ai-rewind-prod"
AI_ID=$(az monitor app-insights component show --app $AI_NAME -g $RG --query id -o tsv)

# Alert on high error rate (>5% over 5 minutes)
az monitor metrics alert create \
  --name "high-error-rate" \
  --resource-group $RG \
  --scopes $AI_ID \
  --condition "avg requests/failed > 5" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --description "Error rate exceeds 5%"

# Alert on high P95 latency (>5 seconds)
az monitor metrics alert create \
  --name "high-latency" \
  --resource-group $RG \
  --scopes $AI_ID \
  --condition "avg requests/duration > 5000" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --description "P95 latency exceeds 5 seconds"
```

### 14.3 Set up Log Analytics queries

Useful KQL queries to save in Log Analytics:

```kusto
// Error distribution by endpoint
requests
| where success == false
| summarize count() by name, resultCode
| order by count_ desc

// Slow requests (>2 seconds)
requests
| where duration > 2000
| project timestamp, name, duration, resultCode
| order by duration desc

// Database connection failures
traces
| where message contains "database" and severityLevel >= 3
| order by timestamp desc
```

---

## 15. Maintenance & Operations

### 15.1 Database migrations

Migrations run automatically on each deploy. To run manually:

```bash
az webapp ssh --name app-backend-rewind-prod --resource-group rg-rewind-prod
# Inside container:
cd /app && alembic upgrade head
```

Check current migration status:
```bash
cd /app && alembic current
```

### 15.2 Rollback a deployment

```bash
# Find the previous image SHA
# Then set the backend to a specific image
az webapp config container set \
  --name app-backend-rewind-prod \
  --resource-group rg-rewind-prod \
  --container-image-name ghcr.io/<YOUR_REPO>/backend:<PREVIOUS_SHA>
```

### 15.3 Database rollback

```bash
# SSH into backend container
az webapp ssh --name app-backend-rewind-prod --resource-group rg-rewind-prod
cd /app && alembic downgrade -1
```

### 15.4 Scale up/down

```bash
# Scale the App Service Plan
az appservice plan update \
  --name asp-rewind-prod \
  --resource-group rg-rewind-prod \
  --sku P1v3    # or B1 for cost savings

# Scale PostgreSQL
az postgres flexible-server update \
  --name pg-rewind-prod \
  --resource-group rg-rewind-prod \
  --sku-name Standard_D2ds_v4
```

### 15.5 Rotate secrets

1. Generate new secret values
2. Update in Key Vault: `az keyvault secret set --vault-name kv-rewind-prod --name <SECRET_NAME> --value "<NEW_VALUE>"`
3. Restart the App Service to pick up new values: `az webapp restart --name <APP_NAME> --resource-group rg-rewind-prod`

---

## 16. Troubleshooting

### Cold starts on B1 tier
- Symptom: First request takes 5-15 seconds
- Fix: Enable "Always On" in App Service configuration, or upgrade to P1v3

### Database connection errors
- Check if your IP is in the PostgreSQL firewall rules
- Verify the connection string in Key Vault
- Check pool settings: `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`

### Blob storage 403 errors
- Verify the storage connection string is correct in Key Vault
- Check that the `sessions` container exists
- Check SAS token expiry if using pre-signed URLs

### Rate limiting (429 responses)
- Default: 100 requests/minute per IP
- Adjust via App Service configuration: `API_RATE_LIMIT=200/minute`
- For the CLI, consider increasing for batch sync operations

### Deploy workflow failures
- Check GitHub Actions logs for specific errors
- Verify `AZURE_CREDENTIALS` secret is still valid (service principals expire)
- Ensure GHCR has write permissions (repo Settings > Actions > General)

### Frontend can't reach backend
- Check CORS configuration on backend App Service
- Verify `NEXT_PUBLIC_API_URL` or `BACKEND_URL` is set correctly
- Check network security (firewall rules, VNet if configured)

---

## Appendix: Environment Variables Reference

### Backend App Service

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Key Vault reference |
| `BACKEND_SECRET` | Shared secret for BFF proxy auth | Key Vault reference |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob Storage | Key Vault reference |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container name | `sessions` |
| `CORS_ORIGINS` | Allowed CORS origins | `["https://rewind.yourdomain.com"]` |
| `API_RATE_LIMIT` | Rate limit (slowapi format) | `100/minute` |
| `MAX_CONTENT_SIZE_BYTES` | Max upload size | `52428800` (50MB) |
| `MAX_DECOMPRESSED_SIZE_BYTES` | Max decompressed size | `268435456` (256MB) |
| `MAX_METADATA_SIZE_BYTES` | Max metadata size | `2097152` (2MB) |
| `DB_POOL_SIZE` | DB connection pool size | `5` |
| `DB_MAX_OVERFLOW` | DB pool overflow | `10` |
| `TRUSTED_HOST` | Domain for HSTS | `rewind.yourdomain.com` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Frontend App Service

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXTAUTH_URL` | Public URL of the frontend | `https://rewind.yourdomain.com` |
| `AUTH_SECRET` | NextAuth JWT encryption secret | Key Vault reference |
| `AUTH_GOOGLE_ID` | Google OAuth Client ID | Key Vault reference |
| `AUTH_GOOGLE_SECRET` | Google OAuth Client Secret | Key Vault reference |
| `BACKEND_URL` | Internal backend URL | `https://app-backend-rewind-prod.azurewebsites.net` |
| `BACKEND_SECRET` | Shared secret for BFF proxy | Key Vault reference |
| `NEXT_PUBLIC_APP_NAME` | App display name | `Rewind` |
| `NEXT_PUBLIC_API_URL` | Backend URL (client-side, dev only) | `http://localhost:8000` |

### CLI

| Variable | Description | Default |
|----------|-------------|---------|
| `REWIND_API_URL` | Backend API URL | `http://localhost:8000` |
| `REWIND_API_KEY` | API key (alternative to `rewind login`) | — |

### GitHub Actions Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Azure service principal JSON |

### GitHub Actions Variables

| Variable | Description |
|----------|-------------|
| `BACKEND_APP_NAME` | Azure backend App Service name |
| `FRONTEND_APP_NAME` | Azure frontend App Service name |
| `RESOURCE_GROUP` | Azure resource group name |
