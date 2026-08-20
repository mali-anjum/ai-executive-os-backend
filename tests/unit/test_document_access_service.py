"""DocumentAccessService — document-level RBAC mirror (owner/admin full access)."""

from app.models.db.tables import Document
from app.services.document_access_service import DocumentAccessService


def _document(
    allowed_roles: list[str] | None = None,
    allowed_departments: list[str] | None = None,
) -> Document:
    return Document(
        filename="policy.pdf",
        storage_path="/tmp/policy.pdf",
        allowed_roles=allowed_roles,
        allowed_departments=allowed_departments,
    )


def test_owner_and_admin_have_full_access():
    svc = DocumentAccessService()
    doc = _document(
        allowed_roles=["employee"], allowed_departments=["engineering"]
    )
    assert svc.can_access_document(doc, role="owner", department=None)
    assert svc.can_access_document(doc, role="admin", department=None)


def test_employee_must_match_role_and_department():
    svc = DocumentAccessService()
    doc = _document(
        allowed_roles=["employee"], allowed_departments=["engineering"]
    )
    assert svc.can_access_document(doc, role="employee", department="engineering")
    assert not svc.can_access_document(doc, role="employee", department="sales")
    assert not svc.can_access_document(doc, role="manager", department="engineering")


def test_unrestricted_document_is_visible_to_everyone():
    svc = DocumentAccessService()
    doc = _document(allowed_roles=None, allowed_departments=None)
    assert svc.can_access_document(doc, role="employee", department=None)
    assert svc.can_access_document(doc, role="manager", department="finance")


def test_user_without_department_cannot_see_department_scoped_doc():
    svc = DocumentAccessService()
    doc = _document(allowed_roles=None, allowed_departments=["engineering"])
    assert not svc.can_access_document(doc, role="employee", department=None)
    assert svc.can_access_document(doc, role="employee", department="engineering")


def test_sqlalchemy_filter_returns_true_for_owner_and_admin():
    svc = DocumentAccessService()
    # true() is the SQLAlchemy boolean literal used to disable filtering.
    assert svc.sqlalchemy_access_filter(role="owner", department=None) is not None
    assert svc.sqlalchemy_access_filter(role="admin", department=None) is not None
