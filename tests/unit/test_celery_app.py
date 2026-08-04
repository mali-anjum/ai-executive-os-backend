"""Celery worker must register background tasks (document ingest, Slack)."""

from app.tasks.celery_app import celery_app


def test_process_document_task_is_registered():
    assert "process_document" in celery_app.tasks


def test_process_slack_event_task_is_registered():
    assert "process_slack_event" in celery_app.tasks


def test_registered_task_names_include_custom_tasks():
    names = {n for n in celery_app.tasks if not n.startswith("celery.")}
    assert "process_document" in names
    assert "process_slack_event" in names
