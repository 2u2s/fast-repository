# 필터링

[English](../en/filtering.md) | **한국어**

> 이 문서는 영어판의 번역입니다. 내용이 다를 경우 영어판이 기준입니다.

`find_all`과 `find_all_paginated`는 SQL `WHERE` 조건으로 변환되는 키워드 필터를 받습니다.

> **참고:** 아래 예제는 비동기 레포지토리를 사용합니다. `SyncCRUDRepository`를 사용하는 경우
> 호출 방식은 동일하며, `await`만 제거하면 됩니다.

## 동등 비교

단순한 `column=value` 키워드는 동등 조건으로 처리됩니다.

```python
await repo.find_all(status="active")        # WHERE status = 'active'
await repo.find_all(status="active", age=36)  # ... AND age = 36
```

여러 키워드는 `AND`로 결합됩니다.

## 연산자 접미사

컬럼 이름에 `__operator`를 추가하면 연산자를 적용할 수 있습니다.

| 키워드                                     | SQL                     |
|-----------------------------------------|-------------------------|
| `column=value`                          | `column = value`        |
| `column__ne=value`                      | `column != value`       |
| `column__in=[a, b]`                     | `column IN (a, b)`      |
| `column__notin=[a, b]`                  | `column NOT IN (a, b)`  |
| `column__gt` / `__ge` / `__lt` / `__le` | `>` / `>=` / `<` / `<=` |
| `column__like` / `__ilike`              | `LIKE` / `ILIKE`        |
| `column__is=None`                       | `IS NULL`               |

```python
await repo.find_all(age__ge=18)             # WHERE age >= 18
await repo.find_all(status__ne="active")    # WHERE status != 'active'
await repo.find_all(id__in=[1, 2, 3])       # WHERE id IN (1, 2, 3)
await repo.find_all(id__notin=[1, 2, 3])    # WHERE id NOT IN (1, 2, 3)
await repo.find_all(name__like="K%")        # WHERE name LIKE 'K%'
await repo.find_all(deleted_at__is=None)    # WHERE deleted_at IS NULL
```

정확한 컬럼 이름이 연산자 접미사보다 우선하므로, 이름 자체에 `__`가 포함된 컬럼도 문제없이 직접 지정할 수 있습니다.

## 커스텀 SQLAlchemy 표현식

키워드 문법으로 표현하기 어려운 조건은 SQLAlchemy 불리언 표현식을 위치 인자로 전달합니다.
이 표현식들은 SQLAlchemy의 `select().where(...)`와 동일한 방식으로 쿼리의 `WHERE` 절에 추가되므로,
`or_`, `and_`, 부정, 함수 호출, JSON 경로 검사 등 표현 가능한 모든 조건을 사용할 수 있습니다.

```python
from sqlalchemy import func, or_

await repo.find_all(or_(User.status == "inactive", User.age >= 30))
await repo.find_all(func.jsonb_path_exists(User.data, "$.role"))
```

위치 인자 표현식과 키워드 필터는 함께 사용할 수 있으며, 모든 조건은 `AND`로 결합됩니다.

```python
await repo.find_all(
    or_(User.age < 18, User.age >= 65),
    status="active",
)
```

`find_all_paginated`도 동일한 표현식을 받으며, `params` 인자 뒤에 위치합니다.

```python
await repo.find_all_paginated(Params(page=1, size=50), User.age >= 30)
```

## 정렬

`find_all`과 `find_all_paginated`는 SQLAlchemy 정렬 표현식을 직접 받는 `order_by` 키워드를 지원합니다.
단일 표현식 또는 리스트로 전달할 수 있습니다.

```python
await repo.find_all(order_by=User.age.desc())
await repo.find_all(order_by=[User.status, User.age.desc()])
```

`find_all_paginated`는 지정한 `order_by` 표현식 뒤에 항상 기본 키를 동순위 결정자로 추가하므로,
페이지 간 정렬이 안정적으로 유지됩니다. `order_by`를 생략하면 기본 키만으로 정렬됩니다.

## 알 수 없는 필터 처리

알 수 없는 컬럼이나 연산자를 지정하면 조용히 무시되는 대신 `InvalidFilterError`(`ValueError`의 서브클래스)가 발생합니다. 따라서 오타가 있어도 필터가 빠진 채로 데이터가 반환되는 일은 없습니다.

```python
from fast_repository import InvalidFilterError

try:
    await repo.find_all(stauts="active")  # 오타
except InvalidFilterError as error:
    ...
```

## 기본 키로 조회

`find`는 기본 키로 엔티티를 조회합니다. 단일 컬럼 키는 위치 인자로 전달합니다.

```python
await repo.find(1)
```

복합키는 각 키 컬럼 이름을 키워드 인자로 지정합니다.

```python
await repo.find(user_id=1, group_id=2)
```

`find`는 엔티티 또는 `None`을 반환합니다. 복합 키를 위치 인자로 전달하거나,
엔티티의 기본 키 컬럼과 일치하지 않는 키를 지정하면 `ValueError`가 발생합니다.

## 락 (Lock) 적용

`find`에 `with_for_update`를 전달하면 락 (`SELECT ... FOR UPDATE`)을 획득합니다.
일반적으로 행을 수정하기 전에 트랜잭션 내에서 사용합니다. `True`를 전달하면 단순 `FOR UPDATE`가 실행됩니다.

```python
user = await repo.find(1, with_for_update=True)
```

`with_for_update`에 딕셔너리(매핑)를 전달하면 해당 옵션이 SQLAlchemy의 `Select.with_for_update`로 그대로 전달됩니다.
사용 가능한 키는 `DbLockInfo` 타입(`nowait`, `read`, `skip_locked`, `key_share`, `of`)에 정의되어 있습니다.

```python
from fast_repository import DbLockInfo

await repo.find(1, with_for_update={"nowait": True})
await repo.find(1, with_for_update={"skip_locked": True})
```

기본값은 `with_for_update=False`이며, 이 경우 락 없이 읽습니다.
락은 데이터베이스 언어에 따라 다르며, `FOR UPDATE`를 지원하지 않는 데이터베이스(예: SQLite)는 이를 무시합니다.

## 페이지네이션

`find_all_paginated`는 동일한 필터를 받으며, fastapi-pagination의 `Page`를 반환합니다.
결과는 기본적으로 기본 키 순으로 정렬됩니다. `order_by`로 직접 정렬 순서를 지정할 수도 있으며,
기본 키는 항상 동순위 결정자로 추가됩니다([정렬](#정렬) 참고).

```python
from fastapi_pagination import Params

page = await repo.find_all_paginated(Params(page=1, size=50), status="active")
page.items   # 현재 페이지의 행 목록
page.total   # 조건에 일치하는 전체 행 수
```

`params`를 생략하면 현재 FastAPI 요청 컨텍스트에서 자동으로 값을 읽어옵니다.

## 개수 세기와 존재 확인

`count`와 `exists`는 `find_all`과 동일한 위치 인자 표현식 및 키워드 필터를 받습니다
(정렬은 적용되지 않습니다). 소프트 삭제 필터도 적용되며, `with_deleted=True`도 지원합니다.

```python
await repo.count(status="active")     # 조건에 일치하는 행의 수
await repo.exists(email="a@b.com")    # 일치하는 행이 있으면 True
```
