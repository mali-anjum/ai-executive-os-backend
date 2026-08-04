"""Per-org integration credentials (Jira, Notion, Google Drive) — Fernet encrypted."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value, encrypt_value
from app.models.db.tables import OrgIntegration


class IntegrationSettingsService:
    async def get_config(
        self, db: AsyncSession, org_id: uuid.UUID, provider: str
    ) -> dict | None:
        result = await db.execute(
            select(OrgIntegration).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.provider == provider,
                OrgIntegration.is_enabled.is_(True),
            )
        )
        row = result.scalar_one_or_none()
        if not row or not row.config_encrypted:
            return None
        plain = decrypt_value(row.config_encrypted)
        return json.loads(plain) if plain else None

    async def upsert_config(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        provider: str,
        config: dict,
    ) -> None:
        result = await db.execute(
            select(OrgIntegration).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.provider == provider,
            )
        )
        row = result.scalar_one_or_none()
        encrypted = encrypt_value(json.dumps(config))
        if row:
            row.config_encrypted = encrypted
            row.is_enabled = True
        else:
            db.add(
                OrgIntegration(
                    org_id=org_id,
                    provider=provider,
                    config_encrypted=encrypted,
                    is_enabled=True,
                )
            )
        await db.commit()

    async def list_providers(self, db: AsyncSession, org_id: uuid.UUID) -> list[str]:
        result = await db.execute(
            select(OrgIntegration.provider).where(
                OrgIntegration.org_id == org_id,
                OrgIntegration.is_enabled.is_(True),
            )
        )
        return [row[0] for row in result.all()]
