"""Tests for SyncCRUDRepository."""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi_pagination import Params
from sqlalchemy import or_, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from fast_repository import InvalidFilterError, SyncCRUDRepository
from tests.models import (
    Membership,
    SyncMembershipRepository,
    SyncUserRepository,
    User,
)


def _compiled_sql(spy: mock.Mock) -> str:
    """Compile the statement passed to a spied ``session.scalar`` for assertions."""
    statement = spy.call_args.args[0]
    return str(statement.compile(dialect=postgresql.dialect()))


def test_find_returns_entity_by_primary_key(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    assert sync_repo.find(sync_users[0].id) is sync_users[0]


def test_find_returns_none_when_missing(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    missing_id = max(user.id for user in sync_users) + 1

    assert sync_repo.find(missing_id) is None


def test_find_returns_entity_by_composite_kwargs(sync_session: Session) -> None:
    repo = SyncMembershipRepository(sync_session)
    membership = Membership(user_id=1, group_id=2, role="admin")
    repo.save(membership)

    assert repo.find(user_id=1, group_id=2) is membership


def test_find_rejects_missing_key(sync_session: Session) -> None:
    repo = SyncMembershipRepository(sync_session)

    with pytest.raises(ValueError):
        repo.find()


def test_find_with_for_update_true_locks_row(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    with mock.patch.object(
        sync_repo.session, "scalar", wraps=sync_repo.session.scalar
    ) as spy:
        found = sync_repo.find(sync_users[0].id, with_for_update=True)

    assert found is sync_users[0]
    assert "FOR UPDATE" in _compiled_sql(spy)


def test_find_all_filters_by_equality(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    active = [user for user in sync_users if user.status == "active"]

    found = sync_repo.find_all(status="active")

    assert sorted(u.id for u in found) == sorted(u.id for u in active)


def test_find_all_applies_ge_operator(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    threshold = sync_users[1].age
    expected = [user for user in sync_users if user.age >= threshold]

    found = sync_repo.find_all(age__ge=threshold)

    assert sorted(u.id for u in found) == sorted(u.id for u in expected)


def test_find_all_rejects_unknown_column(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    with pytest.raises(InvalidFilterError):
        sync_repo.find_all(unknown_column="value")


def test_find_all_accepts_custom_criterion(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    expected = [u for u in sync_users if u.status == "inactive" or u.age >= 30]

    found = sync_repo.find_all(or_(User.status == "inactive", User.age >= 30))

    assert sorted(u.id for u in found) == sorted(u.id for u in expected)


def test_find_all_combines_criteria_with_keyword_filters(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    found = sync_repo.find_all(
        or_(User.status == "inactive", User.age >= 30), status="active"
    )

    expected = [
        u
        for u in sync_users
        if u.status == "active" and (u.status == "inactive" or u.age >= 30)
    ]
    assert sorted(u.id for u in found) == sorted(u.id for u in expected)


def test_find_all_paginated_returns_requested_page(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    page_size = len(sync_users) - 1

    page = sync_repo.find_all_paginated(Params(page=1, size=page_size))

    assert page.total == len(sync_users)
    assert len(page.items) == page_size


def test_save_persists_new_entity(sync_repo: SyncUserRepository) -> None:
    saved = sync_repo.save(User(name="new-user", status="active", age=25))

    assert saved.id
    assert sync_repo.find(saved.id) is saved


def test_save_all_persists_multiple_entities(sync_repo: SyncUserRepository) -> None:
    new_users = [
        User(name="new-user-0", status="active", age=25),
        User(name="new-user-1", status="inactive", age=35),
    ]

    saved = sync_repo.save_all(new_users)

    found = sync_repo.find_all(id__in=[user.id for user in saved])
    assert len(found) == len(new_users)


def test_save_flushes_without_committing_when_autocommit_false(
    sync_repo: SyncUserRepository, sync_session: Session
) -> None:
    saved = sync_repo.save(
        User(name="new-user", status="active", age=25), autocommit=False
    )

    assert saved.id  # flushed: primary key populated
    sync_session.rollback()
    assert sync_repo.find(saved.id) is None  # not committed


def test_delete_removes_entity(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    target_id = sync_users[0].id

    sync_repo.delete(sync_users[0])

    assert sync_repo.find(target_id) is None


def test_delete_all_removes_all_entities(
    sync_repo: SyncUserRepository, sync_users: list[User]
) -> None:
    target_ids = [user.id for user in sync_users]

    sync_repo.delete_all(sync_users)

    assert not sync_repo.find_all(id__in=target_ids)


def test_stmt_defaults_to_select_entity(sync_repo: SyncUserRepository) -> None:
    assert str(sync_repo.stmt) == str(select(User))


def test_find_all_uses_class_declared_stmt(
    sync_session: Session, sync_users: list[User]
) -> None:
    active = [user for user in sync_users if user.status == "active"]

    class ActiveUserRepository(
        SyncCRUDRepository[User], stmt=select(User).where(User.status == "active")
    ):
        """Repository declaring its base statement at class-definition time."""

    repo = ActiveUserRepository(sync_session)

    found = repo.find_all()

    assert sorted(u.id for u in found) == sorted(u.id for u in active)


def test_init_without_entity_raises() -> None:
    class Broken(SyncCRUDRepository):  # type: ignore[type-arg]
        """Subclassed without a concrete entity."""

    with pytest.raises(TypeError):
        Broken(mock.Mock())
