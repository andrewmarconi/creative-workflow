docker:      docker compose up
django:      uv run manage.py runserver
worker:      uv run celery -A cw worker -Q default --loglevel=info --pool=solo
enhancement: uv run celery -A cw worker -Q enhancement --loglevel=info --pool=solo
