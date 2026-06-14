# fast-repository

[English](https://github.com/2u2s/fast-repository/blob/main/README.md) | **한국어**

FastAPI + SQLAlchemy를 위한 interface-first 레포지토리 패턴.

레포지토리 인터페이스만 선언하면 구현은 저절로 따라옵니다.

## 필요성

레포지토리 패턴은 도메인 계층이 추상에 의존하도록 유지해 주지만, 엔티티마다 동일한 CRUD 구현을 반복 작성하는 것은 상당한 보일러플레이트입니다.
`fast-repository`는 패턴을 그대로 유지하면서 그 보일러플레이트를 제거합니다:

```python
from abc import ABC

from fast_repository import AbstractCRUDRepository, CRUDRepository

# 도메인 계층: 이 인터페이스에 의존합니다.
class AbstractUserRepository(AbstractCRUDRepository[User], ABC): ...

# 인프라 계층: 보일러플레이트 없이 모든 CRUD 메서드 제공.
class UserRepository(CRUDRepository[User], AbstractUserRepository): ...
```

엔티티 클래스는 클래스 정의 시점에 제네릭 인수(`CRUDRepository[User]`)로부터 캡처되므로, 생성자 연결도, 메타클래스 관련 학습 부담도 없습니다.

동기 `Session`을 사용하는 경우, `SyncCRUDRepository`와 `AbstractSyncCRUDRepository`가 `async`/`await` 없이 동일한 API를 제공합니다.

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

기본 `stmt`를 선언하여 관계 로딩 방식을 변경하거나, 모든 읽기 작업에 기본 필터를 적용할 수 있습니다. 클래스 키워드 인수로 전달합니다:

```python
class UserRepository(
    CRUDRepository[User],
    stmt=select(User).options(selectinload(User.posts)),
):
    ...
```

`stmt`를 생략하면 읽기 작업은 기본적으로 `select(User)`를 사용합니다. 런타임에 동적으로 변경하려면 인스턴스에서 `self.stmt`를 직접 할당할 수 있습니다.

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
- [쿼리 커스터마이징](https://github.com/2u2s/fast-repository/blob/main/docs/ko/customizing-queries.md) — 관계를 즉시 로드(eager-load)하거나 모든 읽기에 기본 필터를 적용하는 방법.
- [트랜잭션](https://github.com/2u2s/fast-repository/blob/main/docs/ko/transactions.md) — `autocommit` 플래그로 커밋을 제어하고 작업을 단위 작업(unit of work)으로 묶는 방법.
- [소프트 삭제](https://github.com/2u2s/fast-repository/blob/main/docs/ko/soft-delete.md) — 행을 실제로 삭제하는 대신 삭제 표시를 남기는 방법.

기본 CRUD, 필터링, `autocommit` 플래그, 간단한 FastAPI 앱을 다루는 실행 가능한 [예제](https://github.com/2u2s/fast-repository/blob/main/examples/README.md)도 제공합니다.

## 라이선스

MIT
