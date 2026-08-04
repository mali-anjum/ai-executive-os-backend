"""
Knowledge document upload — admin stores files, Celery processes into vectors.

202 Accepted + process_document.delay. Feeds KnowledgeAgent retrieval; unrelated
to Slack tickets.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.tables import User

from app.core.database import get_db
from app.models.http.responses import STANDARD_ERROR_RESPONSES
from app.core.feature_flags import flags
from app.core.security import AuthContext, get_current_user, require_admin, tenant_org_id
from app.models.http.schemas import DocumentAccessUpdate, DocumentResponse, IngestResponse
from app.models.internal.coerce import as_document_status
from app.services.document_access_service import DocumentAccessService
from app.services.document_service import DocumentService
from app.tasks.document_tasks import process_document

router = APIRouter()


async def _load_user_department(db: AsyncSession, auth: AuthContext) -> str | None:
    result = await db.execute(select(User.department).where(User.id == auth.user_id))
    return result.scalar_one_or_none()


@router.post(
    "/ingest",
    status_code=202,
    response_model=IngestResponse,
    responses=STANDARD_ERROR_RESPONSES,
)
async def ingest_document(
    file: UploadFile = File(...),
    allowed_departments: str | None = Form(default=None),
    allowed_roles: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.DOCUMENT_UPLOAD_ENABLED:
        raise HTTPException(status_code=404, detail="Document upload is not enabled")

    suffix = (file.filename or "").lower()
    if not any(suffix.endswith(ext) for ext in [".pdf", ".docx", ".md", ".markdown", ".txt"]):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    dept_list = (
        [d.strip() for d in allowed_departments.split(",") if d.strip()]
        if allowed_departments
        else None
    )
    role_list = (
        [r.strip() for r in allowed_roles.split(",") if r.strip()]
        if allowed_roles
        else None
    )

    service = DocumentService()
    document = await service.save_upload(
        db,
        file,
        user_id=auth.user_id,
        org_id=org_id or auth.org_id,
        allowed_departments=dept_list,
        allowed_roles=role_list,
    )
    process_document.delay(str(document.id))

    return IngestResponse(
        document_id=document.id,
        status=as_document_status(document.status),
        message="Document queued for background processing",
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    service = DocumentService()
    department = await _load_user_department(db, auth)
    return await service.list_documents(
        db,
        org_id=org_id or auth.org_id,
        user_role=auth.role,
        user_department=department,
        rbac_enabled=flags.DOCUMENT_RBAC_ENABLED,
    )


@router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    service = DocumentService()
    document = await service.get_document(
        db, document_id, org_id=org_id or auth.org_id
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if flags.DOCUMENT_RBAC_ENABLED:
        department = await _load_user_department(db, auth)
        access = DocumentAccessService()
        if not access.can_access_document(
            document,
            role=auth.role,
            department=department,
        ):
            raise HTTPException(status_code=403, detail="Access denied")
    path = Path(document.storage_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file missing on disk")
    return FileResponse(
        path,
        media_type=document.mime_type or "application/octet-stream",
        filename=document.filename,
    )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    service = DocumentService()
    deleted = await service.delete_document(
        db,
        document_id,
        org_id=org_id or auth.org_id,
        user_id=auth.user_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.patch("/documents/{document_id}/access", response_model=DocumentResponse)
async def update_document_access(
    document_id: uuid.UUID,
    body: DocumentAccessUpdate,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    org_id: uuid.UUID | None = Depends(tenant_org_id),
):
    if not flags.DOCUMENT_RBAC_ENABLED:
        raise HTTPException(status_code=404, detail="Document RBAC is not enabled")
    service = DocumentService()
    document = await service.update_access(
        db,
        document_id,
        org_id=org_id or auth.org_id,
        allowed_departments=body.allowed_departments,
        allowed_roles=body.allowed_roles,
        user_id=auth.user_id,
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document
