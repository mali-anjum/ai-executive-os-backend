from app.core.rbac import (
    can_assign_role,
    can_manage_members,
    is_leadership,
    member_admin_roles,
)


def test_manage_members_only_owner_or_admin() -> None:
    assert can_manage_members("owner") is True
    assert can_manage_members("admin") is True
    assert can_manage_members("manager") is False
    assert can_manage_members("employee") is False


def test_only_owner_can_assign_owner_role() -> None:
    assert can_assign_role("owner", "owner") is True
    assert can_assign_role("admin", "owner") is False
    assert can_assign_role("manager", "owner") is False


def test_admin_can_assign_non_owner_roles() -> None:
    assert can_assign_role("owner", "admin") is True
    assert can_assign_role("admin", "manager") is True
    assert can_assign_role("owner", "employee") is True
    assert can_assign_role("admin", "employee") is True


def test_manager_cannot_assign_any_role() -> None:
    assert can_assign_role("manager", "employee") is False


def test_leadership_includes_owner() -> None:
    assert is_leadership("owner") is True
    assert is_leadership("admin") is True
    assert is_leadership("manager") is True
    assert is_leadership("employee") is False


def test_member_admin_roles_expose_owner_and_admin() -> None:
    assert member_admin_roles() == {"owner", "admin"}
