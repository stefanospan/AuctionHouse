web: gunicorn application:app
worker: celery -A auction_tasks.celery worker --loglevel=info
beat: celery -A auction_tasks.celery beat --loglevel=info
