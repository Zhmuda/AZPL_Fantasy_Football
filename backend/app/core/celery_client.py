"""Publishes task messages onto the same Redis broker the collector's Celery
worker consumes — lets the admin panel trigger a resync without importing any
collector code (backend and collector are separate services/images)."""
from celery import Celery

from app.core.config import settings

celery_client = Celery("admin_dispatch", broker=settings.REDIS_URL)


def send_task(name: str, args: list):
    # Must match the collector worker's queue (celery_app.py: task_default_queue = "default")
    celery_client.send_task(name, args=args, queue="default")
