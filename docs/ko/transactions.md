# 트랜잭션

[English](../en/transactions.md) | **한국어**

> 이 문서는 영어판의 번역입니다. 내용이 다를 경우 영어판이 기준입니다.

쓰기 메서드인 `save`, `save_all`, `delete`, `delete_all`은 기본적으로 커밋을 합니다.
`autocommit=False`를 전달하면 트랜잭션을 열린 상태로 유지하며 직접 커밋할 수 있습니다.
이 방식으로 여러 작업을 하나의 작업 단위로 묶습니다.

> **참고:** 예제는 비동기 레포지토리를 기준으로 합니다. `SyncCRUDRepository`도 `await` 없이 동일하게 동작합니다.

## Commit (기본 동작)

각 쓰기 메서드는 즉시 플러시하고 커밋합니다:

```python
await repo.save(user)          # INSERT/UPDATE, then COMMIT
await repo.delete(user)        # DELETE, then COMMIT
```

읽기 메서드(`find`, `find_all`, `find_all_paginated`)는 커밋하지 않습니다.

## Flush — `autocommit=False`

`autocommit=False`를 사용하면 쓰기를 플러시하지만 커밋하지는 않습니다.
SQL은 전송되어 기본 키 같은 서버 생성 값이 채워지지만, 트랜잭션은 열린 상태로 유지되어 직접 커밋하거나 롤백할 수 있습니다.

```python
user = await repo.save(User(name="Ada"), autocommit=False)
print(user.id)            # 플러시로 채워진 값

await repo.session.commit()   # 또는 .rollback()
```

## 여러 작업을 한 트랜잭션으로 묶기

모든 쓰기에 `autocommit=False`를 전달하고 마지막에 한 번만 커밋하면, 전체 작업 단위가 모두 반영되거나 하나도 반영되지 않습니다:

```python
await accounts.save(debit, autocommit=False)
await accounts.save(credit, autocommit=False)
await accounts.session.commit()   # 둘 다 반영, 오류 시 둘 다 취소
```

FastAPI에서는 세션을 yield하는 의존성에 이 패턴을 적용하는 경우가 많습니다. 
라우트 핸들러는 `autocommit=False`로 레포지토리를 호출하고, 요청이 완료되면 의존성이 커밋합니다.

## 락 (Lock) 획득

트랜잭션 내에서 업데이트를 위해 락을 얻는 방식은 [필터링 가이드](filtering.md#행-잠금)의 `with_for_update`를 참고합니다.
