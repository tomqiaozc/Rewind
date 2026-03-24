"""Load test script for Rewind API.

This script is a placeholder for running load tests against a deployed
Rewind instance. It requires a running PostgreSQL + Blob Storage + App Service
stack to test against.

Usage (after Azure provisioning):
    python scripts/load_test.py --url https://api.example.com --api-key rw_...

Test plan:
    1. Concurrent session ingests (100 sessions, 10 concurrent workers)
    2. Search under load (10 concurrent FTS queries during ingest)
    3. Health check response time under load
    4. Target: ingest 100 concurrent sessions without errors, p95 latency < 5s
"""
from __future__ import annotations

# TODO: Implement after Azure provisioning
# - Use httpx with asyncio for concurrent requests
# - Generate synthetic CanonicalSession data
# - Measure p95/p99 latency
# - Report pass/fail against targets
