"""Rewind Backend — FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.ingest import router as ingest_router
from src.api.search import router as search_router
from src.api.sessions import router as sessions_router
from src.api.stats import router as stats_router
from src.config import settings

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


# Register routers
app.include_router(ingest_router)
app.include_router(sessions_router)
app.include_router(search_router)
app.include_router(stats_router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
