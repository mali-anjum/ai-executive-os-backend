from app.models.internal.coerce import as_user_role


def test_as_user_role_admin() -> None:
    assert as_user_role("admin") == "admin"


def test_as_user_role_manager() -> None:
    assert as_user_role("manager") == "manager"


def test_as_user_role_defaults_to_employee() -> None:
    assert as_user_role("employee") == "employee"
    assert as_user_role("unknown") == "employee"
