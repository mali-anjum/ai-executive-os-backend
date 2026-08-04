"""
Background job runtime — Redis broker (Upstash in prod).

Two tasks: process_document (Knowledge) and process_slack_event (Tasks). API stays
fast by .delay() here; workers run separately from uvicorn.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "sop_automator",
    broker=settings.redis_url_for_celery,
    backend=settings.redis_url_for_celery,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.slack_tasks",
        "app.tasks.connector_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Worker entrypoint is `-A app.tasks.celery_app.celery_app` — import tasks here so they register.
import app.tasks.document_tasks as _document_tasks  # noqa: F401
import app.tasks.slack_tasks as _slack_tasks  # noqa: F401
import app.tasks.connector_tasks as _connector_tasks  # noqa: F401
