web: gunicorn application:app
worker: celery -A auction_tasks.celery worker --loglevel=info
