"""Tests for CRUDRepository."""

from __future__ import annotations

import pytest
from fastapi_pagination import Params
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fast_repository import CRUDRepository, InvalidFilterError
from tests.models import Membership, MembershipRepository, User, UserRepository


@pytest.mark.asyncio
async def test_find_returns_entity_by_primary_key(
    repo: UserRepository, users: list[User]
) -> None:
    found = await repo.find(users[0].id)

    assert found is users[0]


@pytest.mark.asyncio
async def test_find_returns_none_when_missing(
    repo: UserRepository, users: list[User]
) -> None:
    missing_id = max(user.id for user in users) + 1

    found = await repo.find(missing_id)

    assert not found


@pytest.mark.asyncio
async def test_find_returns_entity_by_composite_kwargs(
    session: AsyncSession,
) -> None:
    repo = MembershipRepository(session)
    membership = Membership(user_id=1, group_id=2, role="admin")
    await repo.save(membership)

    found = await repo.find(user_id=1, group_id=2)

    assert found is membership


@pytest.mark.asyncio
async def test_find_returns_none_for_missing_composite_key(
    session: AsyncSession,
) -> None:
    repo = MembershipRepository(session)
    await repo.save(Membership(user_id=1, group_id=2, role="admin"))

    found = await repo.find(user_id=1, group_id=99)

    assert found is None


@pytest.mark.asyncio
async def test_find_rejects_positional_composite_key(
    session: AsyncSession,
) -> None:
    repo = MembershipRepository(session)

    with pytest.raises(ValueError):
        await repo.find(1)


@pytest.mark.asyncio
async def test_find_rejects_unknown_composite_kwargs(
    session: AsyncSession,
) -> None:
    repo = MembershipRepository(session)

    with pytest.raises(ValueError):
        await repo.find(user_id=1, role="admin")


@pytest.mark.asyncio
async def test_find_rejects_mixing_positional_and_keyword_keys(
    session: AsyncSession,
) -> None:
    repo = MembershipRepository(session)

    with pytest.raises(ValueError):
        await repo.find(1, group_id=2)


@pytest.mark.asyncio
async def test_find_rejects_missing_key(session: AsyncSession) -> None:
    repo = MembershipRepository(session)

    with pytest.raises(ValueError):
        await repo.find()


@pytest.mark.asyncio
async def test_find_all_filters_by_equality(
    repo: UserRepository, users: list[User]
) -> None:
    active_users = [user for user in users if user.status == "active"]

    found = await repo.find_all(status="active")

    assert sorted(user.id for user in found) == sorted(user.id for user in active_users)


@pytest.mark.asyncio
async def test_find_all_treats_string_value_as_equality(
    repo: UserRepository, users: list[User]
) -> None:
    found = await repo.find_all(name=users[0].name)

    assert [user.id for user in found] == [users[0].id]


@pytest.mark.asyncio
async def test_find_all_filters_by_in_clause(
    repo: UserRepository, users: list[User]
) -> None:
    target_users = users[:2]

    found = await repo.find_all(id__in=[user.id for user in target_users])

    assert sorted(user.id for user in found) == sorted(user.id for user in target_users)


@pytest.mark.asyncio
async def test_find_all_accepts_explicit_in_suffix(
    repo: UserRepository, users: list[User]
) -> None:
    target_users = users[:2]

    found = await repo.find_all(id__in=[user.id for user in target_users])

    assert sorted(user.id for user in found) == sorted(user.id for user in target_users)


@pytest.mark.asyncio
async def test_find_all_applies_ge_operator(
    repo: UserRepository, users: list[User]
) -> None:
    threshold = users[1].age
    expected_users = [user for user in users if user.age >= threshold]

    found = await repo.find_all(age__ge=threshold)

    assert sorted(user.id for user in found) == sorted(user.id for user in expected_users)


@pytest.mark.asyncio
async def test_find_all_applies_is_operator(
    repo: UserRepository, session: AsyncSession, users: list[User]
) -> None:
    users[0].nickname = "nick"
    await session.commit()

    found = await repo.find_all(nickname__is=None)

    assert all(user.id != users[0].id for user in found)


@pytest.mark.asyncio
async def test_find_all_rejects_unknown_column(
    repo: UserRepository, users: list[User]
) -> None:
    with pytest.raises(InvalidFilterError):
        await repo.find_all(unknown_column="value")


@pytest.mark.asyncio
async def test_find_all_rejects_unknown_operator(
    repo: UserRepository, users: list[User]
) -> None:
    with pytest.raises(InvalidFilterError):
        await repo.find_all(age__between=(users[0].age, users[-1].age))


@pytest.mark.asyncio
async def test_find_all_paginated_returns_requested_page(
    repo: UserRepository, users: list[User]
) -> None:
    page_size = len(users) - 1

    page = await repo.find_all_paginated(params=Params(page=1, size=page_size))

    assert page.total == len(users)
    assert len(page.items) == page_size


@pytest.mark.asyncio
async def test_find_all_paginated_applies_filters(
    repo: UserRepository, users: list[User]
) -> None:
    active_users = [user for user in users if user.status == "active"]

    page = await repo.find_all_paginated(
        params=Params(page=1, size=len(users)), status="active"
    )

    assert page.total == len(active_users)


@pytest.mark.asyncio
async def test_save_persists_new_entity(repo: UserRepository) -> None:
    user = User(name="new-user", status="active", age=25)

    saved = await repo.save(user)

    assert saved.id
    assert await repo.find(saved.id) is saved


@pytest.mark.asyncio
async def test_save_all_persists_multiple_entities(repo: UserRepository) -> None:
    new_users = [
        User(name="new-user-0", status="active", age=25),
        User(name="new-user-1", status="inactive", age=35),
    ]

    saved = await repo.save_all(new_users)

    found = await repo.find_all(id__in=[user.id for user in saved])
    assert len(found) == len(new_users)


@pytest.mark.asyncio
async def test_delete_removes_entity(repo: UserRepository, users: list[User]) -> None:
    target_id = users[0].id

    await repo.delete(users[0])

    assert not await repo.find(target_id)


@pytest.mark.asyncio
async def test_delete_all_removes_all_entities(
    repo: UserRepository, users: list[User]
) -> None:
    target_ids = [user.id for user in users]

    await repo.delete_all(users)

    assert not await repo.find_all(id__in=target_ids)


@pytest.mark.asyncio
async def test_stmt_defaults_to_select_entity(repo: UserRepository) -> None:
    assert str(repo.stmt) == str(select(User))


@pytest.mark.asyncio
async def test_find_all_uses_user_declared_stmt(
    session: AsyncSession, users: list[User]
) -> None:
    active_users = [user for user in users if user.status == "active"]
    repo = UserRepository(session)
    repo.stmt = select(User).where(User.status == "active")

    found = await repo.find_all()

    assert sorted(user.id for user in found) == sorted(
        user.id for user in active_users
    )


@pytest.mark.asyncio
async def test_find_all_uses_class_declared_stmt(
    session: AsyncSession, users: list[User]
) -> None:
    active_users = [user for user in users if user.status == "active"]

    class ActiveUserRepository(
        CRUDRepository[User], stmt=select(User).where(User.status == "active")
    ):
        """Repository declaring its base statement at class-definition time."""

    repo = ActiveUserRepository(session)

    found = await repo.find_all()

    assert sorted(user.id for user in found) == sorted(
        user.id for user in active_users
    )


@pytest.mark.asyncio
async def test_subclass_inherits_class_declared_stmt(
    session: AsyncSession, users: list[User]
) -> None:
    active_users = [user for user in users if user.status == "active"]

    class ActiveUserRepository(
        CRUDRepository[User], stmt=select(User).where(User.status == "active")
    ):
        """Repository declaring a custom base statement."""

    class ChildRepository(ActiveUserRepository):
        """Subclass that should inherit the parent's custom statement."""

    repo = ChildRepository(session)

    found = await repo.find_all()

    assert sorted(user.id for user in found) == sorted(
        user.id for user in active_users
    )


@pytest.mark.asyncio
async def test_init_subclass_inherits_entity_from_parent(
    session: AsyncSession,
) -> None:
    class AdminUserRepository(UserRepository):
        """Repository inheriting the entity from its parent."""

    admin_repo = AdminUserRepository(session)

    assert not await admin_repo.find_all(name="nobody")
