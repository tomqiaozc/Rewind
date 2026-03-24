"""Rewind Backend — FastAPI application entry point."""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.ingest import router as ingest_router
from src.api.projects import router as projects_router
from src.api.search import router as search_router
from src.api.sessions import router as sessions_router
from src.api.stats import router as stats_router
from src.api.tags import router as tags_router
from src.config import settings
from src.db.session import get_db
from src.middleware.rate_limit import setup_rate_limiting
from src.middleware.request_logging import RequestLoggingMiddleware
from src.middleware.security_headers import SecurityHeadersMiddleware

app = FastAPI(
    title="Rewind API",
    version="0.1.0",
    description="AI coding session intelligence platform",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
setup_rate_limiting(app)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request logging
app.add_middleware(RequestLoggingMiddleware)


# Register routers
app.include_router(ingest_router)
app.include_router(sessions_router)
app.include_router(search_router)
app.include_router(stats_router)
app.include_router(tags_router)
app.include_router(projects_router)


@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:  # noqa: B008
    """Health check with DB connectivity test."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "version": "0.1.0",
    }
