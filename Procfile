docker:      docker compose up
django:      uv run manage.py runserver
worker:      PYTHONPATH=src uv run celery -A cw worker -Q default -E --loglevel=info --pool=solo
flower:      PYTHONPATH=src uv run celery -A cw flower --port=5555
