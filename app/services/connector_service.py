"""Notion and Google Drive connectors — fetch content and ingest as documents."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db.tables import ConnectorSync, Document
from app.services.integration_settings_service import IntegrationSettingsService
from app.tasks.document_tasks import process_document

logger = logging.getLogger(__name__)


class ConnectorService:
    async def list_syncs(
        self, db: AsyncSession, org_id: uuid.UUID
    ) -> list[ConnectorSync]:
        result = await db.execute(
            select(ConnectorSync)
            .where(ConnectorSync.org_id == org_id)
            .order_by(ConnectorSync.last_synced_at.desc().nullslast())
        )
        return list(result.scalars().all())

    async def resync_org_connectors(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        settings_svc: IntegrationSettingsService,
    ) -> int:
        syncs = await self.list_syncs(db, org_id)
        count = 0
        for sync_row in syncs:
            if not sync_row.document_id:
                continue
            doc_result = await db.execute(
                select(Document).where(Document.id == sync_row.document_id)
            )
            document = doc_result.scalar_one_or_none()
            if not document:
                continue
            try:
                if sync_row.connector == "notion":
                    config = await settings_svc.get_config(db, org_id, "notion")
                    token = (config or {}).get("api_token")
                    if not token:
                        continue
                    await self.sync_notion_page(
                        db,
                        org_id=org_id,
                        user_id=document.user_id or org_id,
                        page_id=sync_row.external_id,
                        api_token=token,
                        allowed_departments=document.allowed_departments,
                        allowed_roles=document.allowed_roles,
                    )
                    count += 1
                elif sync_row.connector == "google_drive":
                    config = await settings_svc.get_config(
                        db, org_id, "google_drive"
                    )
                    token = (config or {}).get("access_token")
                    if not token:
                        continue
                    await self.sync_google_drive_file(
                        db,
                        org_id=org_id,
                        user_id=document.user_id or org_id,
                        file_id=sync_row.external_id,
                        access_token=token,
                        allowed_departments=document.allowed_departments,
                        allowed_roles=document.allowed_roles,
                    )
                    count += 1
            except Exception:
                logger.exception(
                    "connector_resync_failed org=%s connector=%s external=%s",
                    org_id,
                    sync_row.connector,
                    sync_row.external_id,
                )
                sync_row.status = "error"
                sync_row.error_message = "Re-sync failed"
                await db.commit()
        return count

    async def sync_notion_page(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        page_id: str,
        api_token: str,
        allowed_departments: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> uuid.UUID:
        text = await self._fetch_notion_page_text(page_id, api_token)
        return await self._ingest_connector_text(
            db,
            org_id=org_id,
            user_id=user_id,
            connector="notion",
            external_id=page_id,
            filename=f"notion-{page_id[:8]}.md",
            text=text,
            allowed_departments=allowed_departments,
            allowed_roles=allowed_roles,
        )

    async def sync_google_drive_file(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        file_id: str,
        access_token: str,
        allowed_departments: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> uuid.UUID:
        text, name = await self._fetch_drive_file_text(file_id, access_token)
        return await self._ingest_connector_text(
            db,
            org_id=org_id,
            user_id=user_id,
            connector="google_drive",
            external_id=file_id,
            filename=name or f"drive-{file_id[:8]}.txt",
            text=text,
            allowed_departments=allowed_departments,
            allowed_roles=allowed_roles,
        )

    async def _ingest_connector_text(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        connector: str,
        external_id: str,
        filename: str,
        text: str,
        allowed_departments: list[str] | None,
        allowed_roles: list[str] | None,
    ) -> uuid.UUID:
        sync_result = await db.execute(
            select(ConnectorSync).where(
                ConnectorSync.org_id == org_id,
                ConnectorSync.connector == connector,
                ConnectorSync.external_id == external_id,
            )
        )
        sync_row = sync_result.scalar_one_or_none()

        upload_root = Path(settings.upload_dir)
        upload_root.mkdir(parents=True, exist_ok=True)
        doc_id = sync_row.document_id if sync_row and sync_row.document_id else uuid.uuid4()
        storage_path = upload_root / f"{doc_id}.md"
        storage_path.write_text(text, encoding="utf-8")

        if sync_row and sync_row.document_id:
            doc_result = await db.execute(
                select(Document).where(Document.id == sync_row.document_id)
            )
            document = doc_result.scalar_one()
            document.status = "pending"
            document.filename = filename
            document.allowed_departments = allowed_departments
            document.allowed_roles = allowed_roles
            document.source_connector = connector
        else:
            document = Document(
                id=doc_id,
                org_id=org_id,
                user_id=user_id,
                filename=filename,
                storage_path=str(storage_path),
                mime_type="text/markdown",
                file_size_bytes=len(text.encode()),
                status="pending",
                allowed_departments=allowed_departments,
                allowed_roles=allowed_roles,
                source_connector=connector,
            )
            db.add(document)

        if sync_row:
            sync_row.status = "synced"
            sync_row.last_synced_at = datetime.now(timezone.utc)
            sync_row.document_id = document.id
            sync_row.error_message = None
        else:
            db.add(
                ConnectorSync(
                    org_id=org_id,
                    connector=connector,
                    external_id=external_id,
                    document_id=document.id,
                    status="synced",
                    last_synced_at=datetime.now(timezone.utc),
                )
            )

        await db.commit()
        await db.refresh(document)
        process_document.delay(str(document.id))
        return document.id

    async def _fetch_notion_page_text(self, page_id: str, token: str) -> str:
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            res = await client.get(blocks_url, headers=headers)
            res.raise_for_status()
            data = res.json()
            parts: list[str] = []
            for block in data.get("results", []):
                block_type = block.get("type")
                payload = block.get(block_type) or {}
                rich = payload.get("rich_text") or []
                line = "".join(item.get("plain_text", "") for item in rich)
                if line.strip():
                    parts.append(line.strip())
            if not parts:
                page_res = await client.get(
                    f"https://api.notion.com/v1/pages/{page_id}",
                    headers=headers,
                )
                page_res.raise_for_status()
                parts.append(f"Notion page {page_id}")
            return "\n\n".join(parts)

    async def _fetch_drive_file_text(self, file_id: str, token: str) -> tuple[str, str]:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            meta_res = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers=headers,
                params={"fields": "name,mimeType"},
            )
            meta_res.raise_for_status()
            meta = meta_res.json()
            name = meta.get("name") or "drive-export.txt"
            mime = meta.get("mimeType") or ""
            if "google-apps" in mime:
                export_mime = "text/plain"
                if "document" in mime:
                    export_mime = "text/plain"
                export_res = await client.get(
                    f"https://www.googleapis.com/drive/v3/files/{file_id}/export",
                    headers=headers,
                    params={"mimeType": export_mime},
                )
                export_res.raise_for_status()
                return export_res.text, name
            content_res = await client.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers=headers,
                params={"alt": "media"},
            )
            content_res.raise_for_status()
            return content_res.text, name
