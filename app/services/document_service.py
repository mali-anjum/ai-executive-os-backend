"""Upload, parse, chunk, embed — queues Celery job for async processing."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db.tables import ActivityLog, Document, DocumentChunk, User
from app.services.chunking_service import ChunkingService
from app.services.document_access_service import DocumentAccessService
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService


class DocumentService:
    """Knowledge ingest orchestrator — file → chunks → vectors in Postgres."""

    def __init__(self) -> None:
        self.parser = DocumentParser()
        self.chunker = ChunkingService()
        self.embedder = EmbeddingService()
        self.vector = VectorService()

    async def save_upload(
        self,
        db: AsyncSession,
        file: UploadFile,
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        allowed_departments: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Document:
        upload_root = Path(settings.upload_dir)
        upload_root.mkdir(parents=True, exist_ok=True)

        doc_id = uuid.uuid4()
        suffix = Path(file.filename or "upload.bin").suffix.lower()
        storage_path = upload_root / f"{doc_id}{suffix}"

        content = await file.read()
        storage_path.write_bytes(content)

        mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".txt": "text/plain",
        }

        document = Document(
            id=doc_id,
            user_id=user_id,
            org_id=org_id,
            filename=file.filename or "unknown",
            storage_path=str(storage_path),
            mime_type=mime_map.get(suffix),
            file_size_bytes=len(content),
            status="pending",
            allowed_departments=allowed_departments,
            allowed_roles=allowed_roles,
        )
        db.add(document)
        await self._log_activity(
            db,
            user_id=user_id,
            org_id=org_id,
            action="document.upload",
            resource_type="document",
            resource_id=document.id,
        )
        await db.commit()
        await db.refresh(document)
        return document

    async def process_document(self, db: AsyncSession, document_id: uuid.UUID) -> None:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = "processing"
        await db.commit()

        try:
            pages = self.parser.extract_text(Path(document.storage_path))
            all_chunks = []
            for page_text, page_num in pages:
                all_chunks.extend(
                    self.chunker.chunk_text(page_text, page_number=page_num)
                )

            if not all_chunks:
                raise ValueError("No text extracted from document")

            db_chunks: list[DocumentChunk] = []
            for chunk in all_chunks:
                embedding = await self.embedder.embed(chunk.content)
                db_chunks.append(
                    DocumentChunk(
                        document_id=document.id,
                        content=chunk.content,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        embedding=embedding,
                    )
                )

            await self.vector.store_chunks(db, db_chunks)
            document.status = "ready"
            document.indexed_at = datetime.now(timezone.utc)
            document.page_count = max(
                (c.page_number or 0 for c in all_chunks), default=0
            ) or None
        except Exception:
            document.status = "error"
            raise
        finally:
            await db.commit()

    async def get_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> Document | None:
        stmt = select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
        if org_id is not None:
            stmt = stmt.where(Document.org_id == org_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        db: AsyncSession,
        org_id: uuid.UUID | None = None,
        *,
        user_role: str = "admin",
        user_department: str | None = None,
        rbac_enabled: bool = False,
    ) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
        if org_id is not None:
            stmt = stmt.where(Document.org_id == org_id)
        if rbac_enabled and user_role != "admin":
            access = DocumentAccessService()
            stmt = stmt.where(
                access.sqlalchemy_access_filter(
                    role=user_role,
                    department=user_department,
                )
            )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_access(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        *,
        org_id: uuid.UUID | None,
        allowed_departments: list[str] | None,
        allowed_roles: list[str] | None,
        user_id: uuid.UUID | None = None,
    ) -> Document | None:
        document = await self.get_document(db, document_id, org_id=org_id)
        if not document:
            return None
        document.allowed_departments = allowed_departments
        document.allowed_roles = allowed_roles
        await self._log_activity(
            db,
            user_id=user_id,
            org_id=org_id,
            action="document.access_update",
            resource_type="document",
            resource_id=document_id,
        )
        await db.commit()
        await db.refresh(document)
        return document

    async def delete_document(
        self,
        db: AsyncSession,
        document_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(Document).where(Document.id == document_id)
        if org_id is not None:
            stmt = stmt.where(Document.org_id == org_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        if not document:
            return False

        path = Path(document.storage_path)
        if path.exists():
            path.unlink()

        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await db.delete(document)
        await self._log_activity(
            db,
            user_id=user_id,
            org_id=org_id,
            action="document.delete",
            resource_type="document",
            resource_id=document_id,
        )
        await db.commit()
        return True

    async def _log_activity(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> None:
        db.add(
            ActivityLog(
                user_id=user_id,
                org_id=org_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )

    async def ensure_default_user(self, db: AsyncSession) -> User:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(email="admin@example.com", role="admin")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
