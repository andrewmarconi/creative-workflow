#!/bin/bash
# Onboarding script for initial project setup
# Run this once to set up the development environment

set -e

echo "========================================"
echo "  Generative Creative Lab - Onboarding"
echo "========================================"
echo ""

# Get the project name prefix for docker volumes
PROJECT_NAME=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]//g')
# Docker Compose uses directory name for volume prefix
COMPOSE_PROJECT=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9\n' '-' | sed 's/-$//')

# Check for existing docker volumes
echo "Checking for existing Docker volumes..."
VOLUMES=$(docker volume ls --format '{{.Name}}' | grep -E "^${COMPOSE_PROJECT}_(postgres_data|valkey_data|loki_data|grafana_data)$" || true)

if [ -n "$VOLUMES" ]; then
    echo ""
    echo "Found existing Docker volumes:"
    echo "$VOLUMES"
    echo ""
    read -p "Do you want to delete these volumes and start fresh? (y/N): " DELETE_VOLUMES

    if [[ "$DELETE_VOLUMES" =~ ^[Yy]$ ]]; then
        echo "Stopping any running containers..."
        docker compose down 2>/dev/null || true

        echo "Deleting volumes..."
        for vol in $VOLUMES; do
            docker volume rm "$vol" && echo "  Deleted: $vol"
        done
        echo "Volumes deleted."
    else
        echo "Keeping existing volumes."
    fi
    echo ""
fi

# Start Docker containers
echo "Starting Docker containers (postgres, valkey, grafana stack)..."
docker compose up -d --wait
echo "All containers healthy."
echo ""

# Install/sync dependencies
echo "Installing Python dependencies with uv..."
uv sync
echo ""

# Run migrations
echo "Running database migrations..."
uv run manage.py migrate
echo ""

# Import data
echo "Importing presets (models, LoRAs)..."
uv run manage.py import_presets
echo ""

echo "Importing core data (languages, LLM models)..."
uv run manage.py import_coredata
echo ""

# Check if prompts data file exists before importing
if [ -f "data/prompts.json" ] || [ -f "data/prompts.txt" ]; then
    echo "Importing prompts..."
    uv run manage.py import_prompts || echo "  (No prompts to import or import failed)"
    echo ""
fi

# Check if adaptations data file exists before importing
if [ -f "data/adaptations.json" ]; then
    echo "Importing adaptations..."
    uv run manage.py import_adaptations || echo "  (No adaptations to import or import failed)"
    echo ""
fi

# Check if markets data file exists before importing
if [ -f "data/markets.json" ]; then
    echo "Importing markets..."
    uv run manage.py import_markets || echo "  (No markets to import or import failed)"
    echo ""
fi

# Create superuser
echo "Creating admin superuser (username: admin, password: admin)..."
DJANGO_SUPERUSER_PASSWORD=admin uv run manage.py createsuperuser \
    --username admin \
    --email admin@localhost \
    --noinput 2>/dev/null || echo "  (Admin user may already exist)"
echo ""

# Stop Docker containers
echo "Stopping Docker containers..."
docker compose down
echo ""

echo "========================================"
echo "  Onboarding Complete!"
echo "========================================"
echo ""
echo "To start the application, run:"
echo "  ./start.sh"
echo ""
echo "Then access:"
echo "  - Django Admin: http://localhost:8000/admin"
echo "  - Grafana:      http://localhost:3000"
echo ""
echo "Login with username 'admin' and password 'admin'"
echo ""
