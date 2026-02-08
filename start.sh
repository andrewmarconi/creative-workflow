#!/bin/bash
# Start all services with proper dependency ordering
# Docker containers must be healthy before Django/Celery start

set -e

echo "Starting Docker containers (postgres, valkey, grafana stack)..."
docker compose up -d --wait

echo "All containers healthy. Starting Django and Celery workers..."
exec uv run honcho start django worker
