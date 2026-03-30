# ── Build stage ──
FROM python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir --prefix=/install .

# ── Runtime stage ──
FROM python:3.9-slim

WORKDIR /app

# Install runtime-only dependencies
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY alembic.ini .
COPY alembic/ alembic/
COPY src/ src/
COPY entrypoint.sh .

# Create non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Entrypoint: run migrations then start gunicorn
CMD ["sh", "entrypoint.sh"]
