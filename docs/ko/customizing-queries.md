# 쿼리 커스터마이징

[English](../en/customizing-queries.md) | **한국어**

> 이 문서는 영어판의 번역입니다. 내용이 다를 경우 영어판이 기준입니다.

모든 조회 메서드(`find`, `find_all`, `find_all_paginated`)는 기본 select 구문인 `stmt`를 토대로 동작합니다.
기본값은 `select(YourEntity)`이며, 이를 재정의하면 관계를 즉시 로드(eager-load)하거나 모든 조회에 필터를 적용할 수 있습니다.

> **Note:** 이 내용은 `SyncCRUDRepository`에도 동일하게 적용됩니다. 
> 예시는 `CRUDRepository`를 사용하지만, `SyncCRUDRepository`로 교체해도 동일하게 동작합니다.

## 클래스 정의 시점

`stmt`를 클래스 키워드 인자로 전달합니다.

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class UserRepository(
    CRUDRepository[User],
    stmt=select(User).options(selectinload(User.posts)),
):
    ...
```

이렇게 하면 모든 조회에서 `posts`를 즉시 로드(eager-load)합니다.
서브클래스는 자체 구문을 선언하지 않는 한 커스텀 `stmt`를 사용합니다.

### 모든 조회에 적용되는 기본 필터

`stmt`는 완전한 select 구문이므로 모든 조회의 범위를 한정하는 `where` 절을 포함할 수 있습니다.
예를 들어 "활성 행만" 반환하는 레포지토리를 선언할 수 있습니다.

```python
class ActiveUserRepository(
    CRUDRepository[User],
    stmt=select(User).where(User.status == "active"),
):
    ...
```

이 레포지토리에서 `find_all()`을 호출하면 활성 사용자만 반환되며, 키워드 필터는 기본 조건 위에 추가됩니다.

## 커스텀 쿼리 메서드 추가

`CRUDRepositoryInterface`는 일반적인 CRUD만 선언합니다. 만약 다른 쿼리가 필요하다면 직접 구현하는 것도 가능합니다.

```python
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import func, select
from typing_extensions import TypedDict

from fast_repository import CRUDRepository, CRUDRepositoryInterface


class ArticleStats(TypedDict):
    author_id: int
    article_count: int
    first_created_at: datetime
    last_created_at: datetime


class ArticleRepositoryInterface(CRUDRepositoryInterface[Article], ABC):
    @abstractmethod
    async def find_stats_by_user(self) -> list[ArticleStats]:
        """작성자별 article 수와 최초/마지막 생성 시점."""


class ArticleRepository(CRUDRepository[Article], ArticleRepositoryInterface):
    async def find_stats_by_user(self) -> list[ArticleStats]:
        result = await self.session.execute(
            select(
                Article.author_id,
                func.count(Article.id),
                func.min(Article.created_at),
                func.max(Article.created_at),
            )
            .group_by(Article.author_id)
            .order_by(Article.author_id)
        )
        return [
            ArticleStats(
                author_id=author_id,
                article_count=count,
                first_created_at=first,
                last_created_at=last,
            )
            for author_id, count, first, last in result.all()
        ]
```

`self.session`을 통해 SQLAlchemy 구문을 직접 생성할 수 있습니다. 호출자는 `ArticleRepositoryInterface`를
사용하기에 다른 메서드와 똑같이 세션을 직접 다루지 않습니다.

[`examples/05_custom_queries.py`](../../examples/05_custom_queries.py)를 참고하세요.

## 필터가 결합되는 방식

[필터링](filtering.md)에서 사용하는 키워드 필터는 커스텀 `stmt`에 추가되는 요소입니다.
기본 구문은 시작점(조인, 로더 옵션, where 절)을 설정하고, 호출별 필터가 그 범위를 더욱 좁힙니다.
두 레이어는 독립적으로 정의되며 자동으로 합성되므로, 커스텀 `stmt`와 키워드 필터를 별도의 처리 없이 함께 사용할 수 있습니다.
