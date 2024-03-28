import os
from celery import Celery

# Get Redis URL from environment variable (set on Heroku)
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

celery = Celery(__name__, broker=redis_url, backend=redis_url)
