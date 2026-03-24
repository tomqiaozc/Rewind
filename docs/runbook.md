# Rewind — Production Runbook

> This runbook will be completed after Azure provisioning. Placeholder sections below.

## Deployment Procedure

1. Push to `main` branch triggers GitHub Actions deploy workflow
2. Docker images built and pushed to GHCR
3. Azure App Service pulls new images
4. Alembic migrations run automatically
5. Health check verifies deployment

## Rollback Procedure

1. Identify the last known good commit SHA
2. Re-deploy using: `az webapp config container set --name <app> --resource-group <rg> --container-image-name ghcr.io/.../backend:<sha>`
3. Verify health check passes
4. If DB migration needs rollback: `alembic downgrade -1`

## Database Migration Procedure

- Migrations run automatically on deploy via `alembic upgrade head`
- Manual migration: `az webapp ssh --name <app> --command "cd /app && alembic upgrade head"`
- Check migration status: `alembic current`

## Monitoring and Alerting

- Azure Application Insights dashboard
- Alert rules configured for:
  - Error rate > 5%
  - P95 latency > 5 seconds
  - Database connection failures
- Log Analytics workspace for structured log queries

## Incident Response

1. Check Application Insights for error spikes
2. Review structured logs in Log Analytics
3. Check health endpoint: `GET /api/health`
4. Verify DB connectivity from health check response
5. Check Azure App Service diagnostics

## Common Troubleshooting

### Cold Starts on App Service B1
- B1 tier has cold start times of 5-15 seconds
- Mitigate with Always On setting (requires B1 or higher)
- Monitor with Application Insights availability tests

### Connection Pooling Issues
- Default pool size: 5, max overflow: 10
- Adjust via `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` env vars
- Monitor with `pg_stat_activity` queries

### Blob Storage Timeouts
- Default timeout is 60 seconds
- Check Azure Storage metrics for throttling
- Verify SAS token expiry if using pre-signed URLs

### Rate Limiting
- Default: 100 requests/minute per IP
- Adjust via `API_RATE_LIMIT` env var (slowapi format)
- Rate-limited responses return HTTP 429
