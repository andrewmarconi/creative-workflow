#!/bin/bash
# Onboarding script for initial project setup
# Run this once to set up the development environment

set -e

echo "========================================"
echo "  Generative Creative Lab - Onboarding"
echo "========================================"
echo ""

# Check for existing Python virtual environment
if [ -d ".venv" ]; then
    echo "Found existing Python virtual environment (.venv)"
    echo ""
    echo "Options:"
    echo "  1) Delete .venv and resync (fresh install)"
    echo "  2) Keep .venv and resync (update packages)"
    echo ""
    read -p "Choose option (1/2) [2]: " VENV_OPTION
    VENV_OPTION=${VENV_OPTION:-2}

    if [ "$VENV_OPTION" = "1" ]; then
        echo "Deleting .venv directory..."
        rm -rf .venv
        echo "Virtual environment deleted."
    else
        echo "Keeping existing virtual environment."
    fi
    echo ""
fi

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

echo "Installing Node.js dependencies..."
npm i
echo ""

# Run migrations
echo "Running database migrations..."
uv run manage.py migrate
echo ""

# Import data
echo "Importing presets (models, LoRAs)..."
uv run manage.py import_presets
echo ""

# Import data
echo "Importing base segments & personas..."
uv run manage.py import_segments
uv run manage.py import_personas
echo ""

echo "Importing reference data (regions, countries, languages, LLM models)..."
uv run manage.py import_reference_data
echo ""

echo "Importing prompt templates..."
uv run manage.py import_prompt_templates
echo ""

echo "Creating pipeline settings (default: Qwen 2.5 7B for all nodes)..."
uv run manage.py shell -c "
from cw.core.models import LLMModel, PipelineSettings
qwen7b = LLMModel.objects.filter(model_id='Qwen/Qwen2.5-7B-Instruct', is_active=True).first()
ps, created = PipelineSettings.objects.get_or_create(pk=1)
if qwen7b:
    ps.global_default_model = qwen7b
    ps.concept_default_model = qwen7b
    ps.culture_default_model = qwen7b
    ps.format_gate_default_model = qwen7b
    ps.culture_gate_default_model = qwen7b
    ps.concept_gate_default_model = qwen7b
    ps.brand_gate_default_model = qwen7b
    ps.save()
    print(f'  Pipeline settings configured with {qwen7b.name}')
else:
    print('  Warning: Qwen 2.5 7B not found, pipeline settings created without defaults')
"
echo ""

# Import brands if data file exists
if [ -f "data/brands.json" ]; then
    echo "Importing brands..."
    uv run manage.py import_brands
    echo ""
fi

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

# Create superuser
echo "Creating admin superuser (username: admin, password: admin)..."
DJANGO_SUPERUSER_PASSWORD=admin uv run manage.py createsuperuser \
    --username admin \
    --email admin@localhost \
    --noinput 2>/dev/null || echo "  (Admin user may already exist)"
echo ""

# Import World Values Survey data from Kaggle
# if [ -n "$KAGGLE_API_TOKEN" ]; then
    echo "Importing World Values Survey data..."
    uv run manage.py import_wvs
    echo ""
# fi

# # Stop Docker containers
# echo "Stopping Docker containers..."
# docker compose down
# echo ""

echo "========================================"
echo "  Onboarding Complete!"
echo "========================================"
echo ""
echo "To start the application, run:"
echo "  ./start.sh"
echo ""
echo "Then access:"
echo "  - Django App:   http://localhost:8000/app"
echo "  - Grafana:      http://localhost:3000"
echo ""
echo "Login with username 'admin' and password 'admin'"
echo ""
