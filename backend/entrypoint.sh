#!/bin/sh
set -e

# Run migrations (non-blocking: if they fail, the app still starts)
echo "Running database migrations..."
alembic upgrade head 2>&1 || echo "WARNING: migrations failed, continuing startup"

# Start the application
exec gunicorn src.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile -
