docker:      docker compose up
django:      uv run manage.py runserver
worker:      uv run celery -A queerchaos worker -Q default --loglevel=info --pool=solo
enhancement: uv run celery -A queerchaos worker -Q enhancement --loglevel=info --pool=solo
