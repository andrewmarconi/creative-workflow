docker:      docker compose up
django:      uv run manage.py runserver
worker:      uv run celery -A cw worker -Q default -E --loglevel=info --pool=solo --logfile=logs/worker_default.log
enhancement: uv run celery -A cw worker -Q enhancement -E --loglevel=info --pool=solo --logfile=logs/worker_enhancement.log
