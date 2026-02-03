"""
ExamGuard Pro - Task Worker
Celery worker for background task processing
"""

from celery import Celery
import os

# Redis URL for message broker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "examguard",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.queue"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minute timeout
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

if __name__ == "__main__":
    celery_app.start()
