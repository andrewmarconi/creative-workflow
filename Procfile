docker:      docker compose up
django:      uv run manage.py runserver
worker:      PYTHONPATH=src uv run celery -A cw worker -Q default -E --loglevel=info --pool=solo
enhancement: PYTHONPATH=src uv run celery -A cw worker -Q enhancement -E --loglevel=info --pool=solo
