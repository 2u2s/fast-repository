# 시작하기

[English](../en/getting-started.md) | **한국어**

> 이 문서는 영어판의 번역입니다. 내용이 다를 경우 영어판이 기준입니다.

이 가이드는 설치부터 레포지토리 동작까지의 과정을 안내합니다.

## 설치

```bash
pip install fast-repository
```

`fast-repository`는 Python 3.10+, SQLAlchemy 2.0+, fastapi-pagination이 필요합니다.
이 의존성들은 자동으로 함께 설치됩니다.

## 1. 엔티티 정의

SQLAlchemy의 declarative 모델이라면 어떤 것이든 사용할 수 있습니다:

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    ...


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    status: Mapped[str]
    age: Mapped[int]
```

## 2. 인터페이스 선언

`AbstractCRUDRepository`를 엔티티와 함께 서브클래싱합니다.
이것이 도메인 레이어가 의존하는 타입으로, SQLAlchemy에 대해 아무것도 알 필요가 없습니다:

```python
from abc import ABC

from fast_repository import AbstractCRUDRepository


class AbstractUserRepository(AbstractCRUDRepository[User], ABC):
    ...
```

## 3. 구현 자동 제공

`CRUDRepository`를 같은 엔티티로 서브클래싱합니다. 모든 CRUD 메서드가 제공되므로
별도로 작성할 내용이 없습니다:

```python
from fast_repository import CRUDRepository


class UserRepository(CRUDRepository[User], AbstractUserRepository):
    ...
```

엔티티 클래스는 클래스 정의 시점에 제네릭 인자(`CRUDRepository[User]`)에서 자동으로 추출되므로,
세션 외에 별도의 생성자 설정이 필요하지 않습니다.

> **참고:** 클래스는 반드시 구체적인 엔티티와 함께 서브클래싱해야 합니다. `CRUDRepository[User]`를
> 직접 인스턴스화하거나 엔티티 없이 서브클래싱하면 `TypeError`가 발생합니다.

## 4. 사용하기

`AsyncSession`으로 레포지토리를 생성하고 메서드를 호출합니다:

```python
repo = UserRepository(session)

user = await repo.save(User(name="Ada", status="active", age=36))
fetched = await repo.find(user.id)
everyone = await repo.find_all()
await repo.delete(user)
```

## 동기 레포지토리

동기 방식의 `Session`을 선호한다면 `SyncCRUDRepository`와 `AbstractSyncCRUDRepository`를 사용합니다. API는 동일하며 `async`/`await`만 없습니다:

```python
from fast_repository import AbstractSyncCRUDRepository, SyncCRUDRepository


class AbstractUserRepository(AbstractSyncCRUDRepository[User], ABC):
    ...


class UserRepository(SyncCRUDRepository[User], AbstractUserRepository):
    ...


repo = UserRepository(session)  # a sqlalchemy.orm.Session

user = repo.save(User(name="Ada", status="active", age=36))
fetched = repo.find(user.id)
everyone = repo.find_all()
repo.delete(user)
```

필터링, `with_for_update`, `autocommit` 플래그, 기본 `stmt` 커스터마이징 모두
비동기 레포지토리와 동일하게 동작합니다.

## 다음 단계

- [필터링](filtering.md) — 키워드 필터와 연산자로 조회합니다.
- [쿼리 커스터마이징](customizing-queries.md) — 관계를 즉시 로드(eager-load)하거나 모든 읽기에 기본 필터를 적용합니다.
- [트랜잭션](transactions.md) — `autocommit` 플래그로 커밋을 제어합니다.
- [소프트 삭제](soft-delete.md) — 행을 제거하는 대신 삭제로 표시합니다.
- [실행 가능한 예제](../../examples/README.md) — 스크립트와 간단한 FastAPI 앱을 제공합니다.
