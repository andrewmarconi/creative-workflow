# QueerChaos Django Setup Guide

Complete setup instructions for the Django-based image generation workflow.

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- uv (Python package manager)
- HuggingFace CLI authentication (`huggingface-cli login`)

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies using uv
uv sync
```

### 2. Start Docker Services

```bash
# Start Postgres and Valkey
docker compose up -d

# Check services are running
docker compose ps
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env if needed (defaults should work for local development)
```

### 4. Run Django Migrations

```bash
# Run migrations to create database schema
uv run manage.py migrate
```

### 5. Create Admin User

```bash
uv run manage.py createsuperuser
```

### 6. Import Presets from JSON

```bash
# Import models and LoRAs from data/presets.json
uv run manage.py import_presets

# Or clear existing and reimport
uv run manage.py import_presets --clear
```

### 7. Start Django Development Server

```bash
uv run manage.py runserver
```

The admin interface will be available at: **http://localhost:8000/admin/**

### 8. Start Celery Workers (Separate Terminal)

```bash
# Start worker for diffusion generation jobs (with MPS support on macOS)
uv run celery -A queerchaos worker -Q default --loglevel=info --pool=solo

# In another terminal, start worker for prompt enhancement
uv run celery -A queerchaos worker -Q enhancement --loglevel=info --pool=solo
```

**Note**: The `--pool=solo` option enables GPU (MPS on Apple Silicon) usage by avoiding fork() issues.

## Workflow

### Admin Interface

Access the Django Unfold admin at: http://localhost:8000/admin/

#### Managing Models & LoRAs

1. **Diffusion Models** - View/edit imported models from presets.json
2. **LoRA Models** - View/edit LoRAs and their compatibility settings

#### Creating Prompts

1. Navigate to **Prompts** → **Add Prompt**
2. Enter your source prompt
3. Optionally set enhancement settings (style, creativity)
4. Save the prompt
5. Use row action **"Enhance"** to queue for enhancement (uses local HuggingFace model)

#### Creating Generation Jobs

**Method 1: From Prompt**
- Go to a Prompt detail page
- Use the inline "Jobs" section or row action **"Create Job"**

**Method 2: Direct Creation**
- Navigate to **Diffusion Jobs** → **Add Diffusion Job**
- Select:
  - Diffusion Model
  - LoRA Model (optional)
  - Prompt
  - Override parameters (optional - uses model defaults if blank)
- Save to auto-queue the job

**Method 3: Bulk Actions**
- Select multiple prompts
- Use bulk action **"Create diffusion jobs for selected prompts"**

#### Monitoring Jobs

- **Status badges**: Pending, Queued, Processing, Completed, Failed
- **Row actions**:
  - **Queue** (for pending jobs)
  - **Retry** (for failed jobs)
  - **Cancel** (for pending/queued jobs)
- **Bulk actions**: Queue, Cancel, Retry failed jobs

#### Viewing Results

- Completed jobs show generated images inline
- Images stored in `media/diffusion/job_<id>/`
- Click images to view full size

## Architecture

### Directory Structure

```
queerchaos/
├── diffusion/              # Django app for diffusion generation
│   ├── models.py          # DiffusionModel, LoraModel, Prompt, DiffusionJob
│   ├── admin.py           # Jazzmin admin with tabs, inlines, row actions
│   ├── tasks.py           # RQ worker tasks
│   └── management/
│       └── commands/
│           └── import_presets.py
├── settings.py            # Django settings (Postgres, Valkey, Jazzmin)
└── urls.py                # URL configuration

lib/                       # Existing Python modules
├── models/                # BaseModel, ZImageTurboModel, FluxModel, QwenImageModel
├── loras/                 # LoRAManager
├── prompt_enhancer.py     # PromptEnhancer, HFPromptEnhancer
└── config.py              # Config utilities

data/
└── presets.json           # Source configuration for models/LoRAs

media/
└── diffusion/             # Generated images
    └── job_<id>/
```

### Data Flow

1. **Import**: `presets.json` → Database (via `import_presets` command)
2. **Prompt Enhancement**: User creates Prompt → Celery worker enhances via HFPromptEnhancer (with MPS on macOS)
3. **Image Generation**: User creates DiffusionJob → Celery worker uses `lib/models/*` to generate (with MPS on macOS)
4. **Results**: Images saved to `media/diffusion/job_<id>/`, paths stored in database

## Celery Workers

### Default Queue (Diffusion Generation)
- Timeout: 3600s (1 hour hard limit, 55min soft limit)
- Handles: Image generation jobs
- Command: `uv run celery -A queerchaos worker -Q default --loglevel=info --pool=solo`
- **Pool**: `solo` - enables MPS (Apple Silicon GPU) usage

### Enhancement Queue (Prompt Enhancement)
- Timeout: 600s (10 minutes)
- Handles: Prompt enhancement via local LLM
- Command: `uv run celery -A queerchaos worker -Q enhancement --loglevel=info --pool=solo`
- **Pool**: `solo` - enables MPS (Apple Silicon GPU) usage

### Monitoring

- Celery Flower (optional): `uv run celery -A queerchaos flower`
- Task results: Check Valkey DB 3 (`redis-cli -p 6379 -n 3`)
- Broker: Check Valkey DB 2 (`redis-cli -p 6379 -n 2`)

## Troubleshooting

### Postgres Connection Failed
```bash
# Check Postgres is running
docker compose ps

# Check logs
docker compose logs postgres

# Restart if needed
docker compose restart postgres
```

### Valkey Connection Failed
```bash
# Check Valkey is running
docker compose ps

# Check logs
docker compose logs valkey
```

### Worker Not Processing Jobs
```bash
# Check worker is running
# Should see: "[INFO/MainProcess] Connected to redis://localhost:6379/2"
# Should see: "[INFO/MainProcess] mingle: searching for neighbors"

# Check Celery Flower (if installed)
uv run celery -A queerchaos flower

# Or check Valkey directly
redis-cli -p 6379 -n 2 KEYS '*'
```

### Model Loading Fails
- Ensure HuggingFace authentication: `huggingface-cli login`
- Check model path in database matches HuggingFace or local path
- Verify you have enough RAM (48GB recommended for large models)

### Import Fails
```bash
# Verify presets.json exists and is valid JSON
cat data/presets.json | python -m json.tool

# Try with --clear flag
uv run manage.py import_presets --clear
```

## Development Commands

```bash
# Create new migration after model changes
uv run manage.py makemigrations

# Apply migrations
uv run manage.py migrate

# Create superuser
uv run manage.py createsuperuser

# Import/reimport presets
uv run manage.py import_presets
uv run manage.py import_presets --clear

# Run dev server
uv run manage.py runserver

# Start Celery workers
uv run celery -A queerchaos worker -Q default --loglevel=info --pool=solo
uv run celery -A queerchaos worker -Q enhancement --loglevel=info --pool=solo

# Django shell
uv run manage.py shell
```

## Production Considerations

1. **Secret Key**: Generate a secure `DJANGO_SECRET_KEY` in `.env`
2. **Debug Mode**: Set `DJANGO_DEBUG=False`
3. **Allowed Hosts**: Configure `ALLOWED_HOSTS` in `settings.py`
4. **Static Files**: Run `uv run manage.py collectstatic`
5. **Process Manager**: Use systemd/supervisor for Django + Celery workers
6. **Reverse Proxy**: Use nginx/caddy in front of Django
7. **Database**: Use managed Postgres service or tune local instance
8. **Media Storage**: Consider S3/Cloudflare R2 for image storage
9. **Monitoring**: Add Sentry for error tracking, Prometheus for metrics

## Features

✓ Django 6.0.1 with Django Unfold admin theme
✓ Postgres 17.x database
✓ Valkey (Redis alternative) for Celery broker
✓ Celery for async task processing with MPS support on macOS
✓ Import models/LoRAs from presets.json
✓ Prompt enhancement using local HuggingFace models (with GPU acceleration)
✓ Image generation via existing lib modules (with GPU acceleration)
✓ Admin UI with tabs, inlines, and row actions
✓ Django media files for image storage
✓ Comprehensive job tracking and monitoring

## Next Steps

- Customize Django Unfold theme in `settings.py`
- Add user authentication and permissions
- Create custom views/APIs beyond admin
- Integrate with frontend framework (React/Vue)
- Add webhook notifications for job completion (Celery signals)
- Implement batch operations
- Add more model/LoRA support
- Set up Celery Beat for scheduled tasks
