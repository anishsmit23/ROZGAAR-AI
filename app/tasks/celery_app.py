from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "rozgaar",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    
    # Task configuration
    task_track_started=True,
    task_time_limit=30 * 60,  # Hard limit 30 minutes
    task_soft_time_limit=25 * 60,  # Soft limit 25 minutes
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker configuration
    worker_prefetch_multiplier=1,  # Prevent worker from prefetching tasks
    worker_max_tasks_per_child=100,  # Worker restart after 100 tasks for memory management
    
    # Retry configuration
    task_acks_late=True,  # Acknowledge tasks only after execution
    task_reject_on_worker_lost=True,  # Retry if worker dies
    
    # Queue configuration
    task_queues=(
        {"name": "agents", "exchange": "agents", "routing_key": "agents.*"},
        {"name": "scrapers", "exchange": "scrapers", "routing_key": "scrapers.*"},
    ),
    task_default_queue="agents",
    task_default_exchange="agents",
    
    # Periodic tasks configuration
    beat_schedule={
        # Add periodic tasks here if needed
        # Example: "check-jobs-every-hour": {
        #     "task": "app.tasks.scraper_tasks.run_scheduled_scrape",
        #     "schedule": crontab(minute=0),  # Every hour
        # },
    },
)

# Auto-discover tasks from modules
celery_app.autodiscover_tasks(["app.tasks"])
