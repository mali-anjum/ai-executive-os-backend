"""Scheduled connector re-sync — refresh Notion / Google Drive indexed documents."""

import asyncio
import logging
import uuid

from sqlalchemy import select

from app.core.database import CeleryAsyncSessionLocal
from app.core.feature_flags import flags
from app.models.db.tables import ConnectorSync, Organization
from app.services.connector_service import ConnectorService
from app.services.integration_settings_service import IntegrationSettingsService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


@celery_app.task(name="resync_connectors_for_org")
def resync_connectors_for_org_task(org_id: str) -> str:
    async def _run():
        if not flags.CONNECTOR_SYNC_ENABLED:
            return "skipped:disabled"
        async with CeleryAsyncSessionLocal() as db:
            service = ConnectorService()
            settings_svc = IntegrationSettingsService()
            count = await service.resync_org_connectors(
                db, org_id=uuid.UUID(org_id), settings_svc=settings_svc
            )
            return f"synced:{count}"

    return _run_async(_run())


@celery_app.task(name="resync_all_connectors")
def resync_all_connectors_task() -> str:
    async def _run():
        if not flags.CONNECTOR_SYNC_ENABLED:
            return "skipped:disabled"
        async with CeleryAsyncSessionLocal() as db:
            result = await db.execute(
                select(Organization.id).distinct()
            )
            org_ids = [row[0] for row in result.all()]
            if not org_ids:
                sync_orgs = await db.execute(
                    select(ConnectorSync.org_id).distinct()
                )
                org_ids = [row[0] for row in sync_orgs.all()]
            service = ConnectorService()
            settings_svc = IntegrationSettingsService()
            total = 0
            for oid in org_ids:
                try:
                    total += await service.resync_org_connectors(
                        db, org_id=oid, settings_svc=settings_svc
                    )
                except Exception:
                    logger.exception("connector_resync_failed org_id=%s", oid)
            return f"synced:{total}"

    return _run_async(_run())
