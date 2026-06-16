# fast-repository

[English](https://github.com/2u2s/fast-repository/blob/main/README.md) | **한국어**

[![PyPI](https://img.shields.io/pypi/v/fast-repository)](https://pypi.org/project/fast-repository/)
[![Python](https://img.shields.io/pypi/pyversions/fast-repository)](https://pypi.org/project/fast-repository/)
[![License](https://img.shields.io/pypi/l/fast-repository)](https://github.com/2u2s/fast-repository/blob/main/LICENSE)
[![Downloads](https://static.pepy.tech/badge/fast-repository/month)](https://pepy.tech/project/fast-repository)

FastAPI + SQLAlchemy를 위한 interface-first 레포지토리 패턴.

레포지토리 인터페이스만 선언하면 구현은 저절로 따라옵니다.

## 필요성

FastAPI에는 기본적으로 레포지토리라는 개념이 없습니다. 공식 튜토리얼은 경로 함수(path operation)가 DB를
직접 접근하거나, 자유 함수들을 모아 둔 느슨한 `crud.py` 모듈을 사용합니다. 데모에는 충분하지만, 앱이 커지
쿼리 로직이 라우트 곳곳에 흩어지고 비즈니스 로직이 SQLAlchemy에 강하게 결합됩니다.

레포지토리 패턴은 한 엔티티의 영속성(persistence)을 책임지는 객체 하나를 두는 방식으로,
다음과 같은 이점이 있습니다:

- **도메인 계층이 구현체가 아니라 인터페이스에 의존합니다.** 비즈니스 로직은
  `UserRepositoryInterface`와만 대화하며, 세션을 임포트하거나 `select()`를 작성하지
  않습니다.
- **DB 없이 테스트할 수 있습니다.** 인터페이스 경계에서 실제 레포지토리를 모킹하여 비즈니스 로직을 위한
  단위 테스트 도입이 가능합니다.
- **쿼리 로직이 한곳에 모입니다.** 필터링, eager-loading, 소프트 삭제 규칙을 엔드포인트마다
  복사·붙여넣기하지 않아도 됩니다.
- **구현을 쉽게 변경할 수 있습니다.** ORM을 바꾸거나, 캐시를 추가하거나, 읽기와 쓰기를
  분리해도 호출 측 코드는 그대로입니다.

문제는, 그 레포지토리를 엔티티마다 직접 작성하는 일 — 각종 조회, 저장, 삭제 함수. 그리고 페이지네이션까지 —
이 매번 똑같은 보일러플레이트라는 점입니다.

**Before** — 코드를 직접 작성하고, 엔티티마다 반복합니다:

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase): ...


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]
    status: Mapped[str]


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find(self, id: int) -> User | None:
        return await self.session.scalar(select(User).where(User.id == id))

    async def find_all(
        self,
        name: str | None = None,
        age: int | None = None,
        status: str | None = None,
    ) -> list[User]:
        stmt = select(User)
        if name is not None:
            stmt = stmt.where(User.name == name)
        if age is not None:
            stmt = stmt.where(User.age == age)
        if status is not None:
            stmt = stmt.where(User.status == status)
        return list((await self.session.scalars(stmt)).all())

    async def count(
        self,
        name: str | None = None,
        age: int | None = None,
        status: str | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(User)
        if name is not None:
            stmt = stmt.where(User.name == name)
        if age is not None:
            stmt = stmt.where(User.age == age)
        if status is not None:
            stmt = stmt.where(User.status == status)
        return await self.session.scalar(stmt) or 0

    async def save(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()

    # ...그리고 exists(), save_all(), delete_all(), find_all_paginated(),
    #    연산자 필터(__in / __ne / __like), 행 잠금, 소프트 삭제까지 —
    #    엔티티마다 전부 다시 작성해야 합니다.
```

**After** — `fast-repository`가 위의 모든 것을 패턴 그대로 제공합니다:

```python
from abc import ABC

from fast_repository import CRUDRepositoryInterface, CRUDRepository

# 도메인 계층: 이 인터페이스에 의존합니다.
class UserRepositoryInterface(CRUDRepositoryInterface[User], ABC): ...

# 인프라 계층: 보일러플레이트 없이 모든 CRUD 메서드 제공.
class UserRepository(CRUDRepository[User], UserRepositoryInterface): ...
```

엔티티 클래스는 클래스 정의 시점에 제네릭 인수(`CRUDRepository[User]`)로부터 캡처되므로, 생성자 연결도, 메타클래스 관련 학습 부담도 없습니다.

동기 `Session`을 사용하는 경우, `SyncCRUDRepository`와 `SyncCRUDRepositoryInterface`가 `async`/`await` 없이 동일한 API를 제공합니다.

## 설치

```bash
pip install fast-repository
```

Python 3.10+, SQLAlchemy 2.0+(비동기 또는 동기), fastapi-pagination이 필요합니다.

## 사용법

```python
repo = UserRepository(session)  # AsyncSession

await repo.find(1)                                # SELECT ... WHERE id = 1
await repo.find(1, with_for_update=True)          # ... FOR UPDATE (행 잠금)
await repo.find(user_id=1, group_id=2)            # 이름으로 복합 키 조회
await repo.find_all(status="active")              # ... WHERE status = 'active'
await repo.find_all(id__in=[1, 2, 3])             # ... WHERE id IN (1, 2, 3)
await repo.find_all(age__ge=18, name__like="K%") # 연산자 접미사 사용
await repo.find_all(or_(User.age < 18, User.age >= 65))  # raw SQLAlchemy 표현식 직접 사용
await repo.find_all(status__ne="active")          # ... WHERE status != 'active'
await repo.find_all(id__notin=[1, 2, 3])          # ... WHERE id NOT IN (1, 2, 3)
await repo.find_all(order_by=User.age.desc())     # ... ORDER BY age DESC
await repo.find_all_paginated(params=Params(page=1, size=50), status="active")  # FastAPI에선 params 생략 가능
await repo.count(status="active")                 # SELECT count(*) ... WHERE status = 'active'
await repo.exists(id=1)                           # SELECT EXISTS(...) -> bool

await repo.save(user)
await repo.save_all(users)
await repo.delete(user)
await repo.delete_all(users)
```

### 필터 문법

| 키워드                                     | SQL                     |
|-----------------------------------------|-------------------------|
| `column=value`                          | `column = value`        |
| `column__in=[a, b]`                     | `column IN (a, b)`      |
| `column__notin=[a, b]`                  | `column NOT IN (a, b)`  |
| `column__ne=value`                      | `column != value`       |
| `column__gt` / `__ge` / `__lt` / `__le` | `>` / `>=` / `<` / `<=` |
| `column__like` / `__ilike`              | `LIKE` / `ILIKE`        |
| `column__is=None`                       | `IS NULL`               |

알 수 없는 컬럼이나 연산자를 사용하면 조용히 무시되는 대신 `InvalidFilterError`가 발생합니다. 오타로 인해 필터가 적용되지 않은 채 데이터가 반환되는 상황을 방지합니다.

### 쿼리 커스터마이징

기본 `stmt`를 선언하여 관계 로딩 방식을 변경하거나, 모든 조회 작업에 기본 필터를 적용할 수 있습니다. 클래스 키워드 인수로 전달합니다:

```python
class UserRepository(
    CRUDRepository[User],
    stmt=select(User).options(selectinload(User.posts)),
):
    ...
```

`stmt`를 생략하면 조회 작업은 기본적으로 `select(User)`를 사용합니다.

### IDE 자동완성을 위한 타입 필터

`find_all`, `count` 등 조회 메서드는 임의의 키워드 필터를 받기 때문에, 타입 체커가 엔티티의 컬럼을 이름으로 제안해 주지 못합니다.
IDE 자동완성 기능을 사용하고 싶다면, 인터페이스 클래스에서 해당 메서드를 다음과 같이 재선언합니다.

```python
from sqlalchemy.sql import ColumnElement


class UserRepositoryInterface(CRUDRepositoryInterface[User], ABC):
    @abstractmethod
    async def find_all(
        self,
        *criteria: ColumnElement[bool],
        status: str | None = None,
        **_,
    ) -> list[User]: ...
```

이제 값이 `UserRepositoryInterface` 타입으로 선언된 곳이라면 에디터가 `status=`를 제안합니다.
더 많은 필터를 노출하려면 키워드를 추가하면 됩니다:

```python
class UserRepositoryInterface(CRUDRepositoryInterface[User], ABC):
    @abstractmethod
    async def find_all(
        self, 
        *criteria: ColumnElement[bool],
        status: str | None = None,
        age: int | None = None,
        **_,
    ) -> list[User]: ...
```

이 효과는 변수가 **인터페이스 타입**으로 선언됐을 때만 적용됩니다.

### FastAPI에서의 페이지네이션

FastAPI 라우트 안에서는 `params`를 직접 넘길 필요가 없습니다.
`response_model`이 `Page[...]`이고 `add_pagination(app)`이 연결되어 있으면,
fastapi-pagination이 쿼리 문자열의 `?page=`/`?size=`를 파싱하고 `find_all_paginated`가 이를 자동으로 가져옵니다.

```python
from fastapi import FastAPI
from fastapi_pagination import Page, add_pagination

app = FastAPI()

@app.get("/users", response_model=Page[UserOut])
async def list_users(repo: UserRepo, status: str | None = None) -> Page[User]:
    filters = {"status": status} if status is not None else {}
    return await repo.find_all_paginated(**filters)  # params는 자동으로 주입

add_pagination(app)
```

## 문서

- [시작하기](https://github.com/2u2s/fast-repository/blob/main/docs/ko/getting-started.md) — 설치, 엔티티 정의, 레포지토리 연결 방법.
- [필터링](https://github.com/2u2s/fast-repository/blob/main/docs/ko/filtering.md) — 키워드 필터, 연산자 접미사, 기본 키 조회, 페이지네이션.
- [쿼리 커스터마이징](https://github.com/2u2s/fast-repository/blob/main/docs/ko/customizing-queries.md) — 관계를 즉시 로드(eager-load)하거나 모든 조회에 기본 필터를 적용하는 방법.
- [트랜잭션](https://github.com/2u2s/fast-repository/blob/main/docs/ko/transactions.md) — `autocommit` 플래그로 커밋을 제어하고 작업을 단위 작업(unit of work)으로 묶는 방법.
- [소프트 삭제](https://github.com/2u2s/fast-repository/blob/main/docs/ko/soft-delete.md) — 행을 실제로 삭제하는 대신 삭제 표시를 남기는 방법.
- [FastAPI 연동](https://github.com/2u2s/fast-repository/blob/main/docs/ko/fastapi.md) — 의존성 주입으로 레포지토리를 라우트에 연결하는 방법.

기본 CRUD, 필터링, `autocommit` 플래그, 간단한 FastAPI 앱을 다루는 실행 가능한 [예제](https://github.com/2u2s/fast-repository/blob/main/examples/README.md)도 제공합니다.

## 라이선스

MIT
