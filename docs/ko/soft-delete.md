# 소프트 삭제 (Soft Delete)

[English](../en/soft-delete.md) | **한국어**

> 이 문서는 영어판의 번역입니다. 내용이 다를 경우 영어판이 기준입니다.

기본적으로 `delete`는 행을 물리적으로 제거합니다.
소프트 삭제를 활성화하면 `delete`는 행을 삭제된 것으로 표시하고, 모든 읽기 메서드는 해당 행을 자동으로 숨깁니다.

> **참고:** 예시는 비동기 레포지토리를 기준으로 합니다. `SyncCRUDRepository`도 `await` 없이 동일하게 동작합니다.

## 활성화하기

엔티티에 소프트 삭제 컬럼을 추가하고 `soft_delete` 클래스 키워드로 해당 컬럼명을 지정합니다. 컬럼 타입은 `datetime`(삭제 전에는 `NULL`, 삭제 시 삭제 시각으로 설정) 또는 `bool`(삭제 시 `True`로 설정)이 가능하며, 타입은 자동으로 감지됩니다:

```python
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class ArticleRepository(CRUDRepository[Article], soft_delete="deleted_at"):
    ...
```

`soft_delete`에는 컬럼 이름 또는 매핑된 어트리뷰트 자체를 전달할 수 있습니다. 어트리뷰트를 전달하면 타입 검사와 리팩터링 안전성이 보장되어, 오타를 런타임이 아닌 정의 시점에 잡을 수 있습니다:

```python
class ArticleRepository(CRUDRepository[Article], soft_delete=Article.deleted_at):
    ...
```

존재하지 않는 컬럼, 또는 `datetime`이나 `bool`이 아닌 컬럼을 지정하면 레포지토리 생성 시 `ValueError`가 발생합니다.

## 삭제하기

`delete`와 `delete_all`은 이제 행을 제거하는 대신 삭제 표시를 남기며, `autocommit` 플래그 동작은 기존과 동일하게 유지됩니다:

```python
await repo.delete(article)       # deleted_at = 현재 시각으로 설정 후 커밋
await repo.delete_all(articles)  # 각 항목에 삭제 표시
```

행을 실제로 제거하려면 `hard=True`를 전달합니다:

```python
await repo.delete(article, hard=True)  # 물리적 DELETE
```

## 읽기

모든 읽기 메서드는 소프트 삭제된 행을 자동으로 제외합니다:

```python
await repo.find(article.id)   # 소프트 삭제 후에는 None 반환
await repo.find_all()         # 소프트 삭제된 행 제외
```

소프트 삭제된 행을 포함하려면 `with_deleted=True`를 전달합니다:

```python
await repo.find(article.id, with_deleted=True)
await repo.find_all(status="archived", with_deleted=True)
```

소프트 삭제 필터는 키워드 필터, 커스텀 표현식, 기본 `stmt` 모두와 `AND`로 결합됩니다.
