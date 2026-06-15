# FastAPI 통합

`fast-repository`는 FastAPI를 위해 설계되었습니다. 레포지토리는 SQLAlchemy 세션만 받으면 되므로
`Depends`에 그대로 끼울 수 있습니다. 이 가이드는 [`examples/fastapi_app/`](../../examples/fastapi_app)의 예제 앱을 따라갑니다.
이 앱은 통합의 각 조각을 쉽게 찾을 수 있도록 역할별로 분리되어 있습니다.

## 프로젝트 구조

| 파일                | 내용                       |
|-------------------|--------------------------|
| `database.py`     | DB 엔진, 세션 메이커            |
| `dependencies.py` | FastAPI 의존성              |
| `dtos.py`         | Pydantic 기반 DTO, 쿼리 파라미터 |
| `routers.py`      | 라우터 엔드포인트 정의             |
| `main.py`         | FastAPI 앱 정의             |

SQLAlchemy 모델과 레포지토리는 공유 파일 [`examples/models.py`](../../examples/models.py)에, 
`User.status`에 쓰이는 enum은 [`examples/enums.py`](../../examples/enums.py)에 있습니다.

## 레포지토리 주입

FastAPI 의존성으로 레포지토리를 선언할 때, 반환 타입을 구현체가 아니라 *추상(abstract)* 인터페이스로 선언하세요.

```python
# dependencies.py
def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AbstractUserRepository:
    return UserRepository(session)


UserRepo = Annotated[AbstractUserRepository, Depends(get_user_repository)]
```

핸들러는 `UserRepo` 별칭만 있으면 됩니다:

```python
@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserIn, repo: UserRepo) -> User:
    return await repo.save(
        User(
            name=body.name,
            status=body.status,
            age=body.age,
        )
    )
```

## 수정(update)은 곧 저장(save)

별도의 update 메서드는 없습니다. 엔티티를 불러와 클라이언트가 보낸 필드를 반영한 뒤
다시 `save`하면 됩니다:

```python
@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate, repo: UserRepo) -> User:
    user = await repo.find(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
    if body.name is not None:
        user.name = body.name
    if body.status is not None:
        user.status = body.status
    if body.age is not None:
        user.age = body.age
    return await repo.save(user)
```

## 쿼리 파라미터로 필터링과 정렬

`find_all_paginated`는 `find_all`과 동일한 키워드 필터를 받습니다.
단순한 `column=value`는 등호 조건이고, `column__operator` 접미사는 `ge` 같은 연산자를 적용합니다.
쿼리 파라미터를 이 필터로 매핑하세요:

```python
@router.get("", response_model=Page[UserOut])
async def list_users(repo: UserRepo, params: Annotated[UserListParams, Depends()]) -> Page[User]:
    filters = {}
    if params.status is not None:
        filters["status"] = params.status
    if params.min_age is not None:
        filters["age__ge"] = params.min_age
    order = User.age.desc() if params.order == "-age" else User.id.asc()
    return await repo.find_all_paginated(order_by=order, **filters)
```

`order_by`는 SQLAlchemy 정렬식을 그대로 받으므로, 예제에서는 `-age` 같은 `order`
값을 `User.age.desc()`로 변환합니다. 실행 가능한 코드에서는 이를 작은 `_order_by`
헬퍼로 분리했습니다. 연산자 전체 목록은 [필터링](filtering.md)을 참고하세요.

## 페이지네이션

`find_all_paginated`는 `fastapi_pagination.Page`를 반환합니다. 요청 안에서는
`params`를 넘기지 않아도 됩니다. `add_pagination(app)`이 fastapi-pagination으로
하여금 쿼리 문자열의 `?page=`와 `?size=`를 자동으로 읽게 해 줍니다:

```python
# main.py
app = FastAPI(lifespan=lifespan)
app.include_router(router)
add_pagination(app)
```

응답을 `Page[UserOut]`로 선언하면 페이지 메타데이터(`total`, `page`, `size`)가
자동으로 채워집니다.

## 에러 처리

`find`는 일치하는 항목이 없으면 `None`을 반환합니다. 이를 404로 바꾸세요:

```python
user = await repo.find(user_id)
if user is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="user not found",
    )
```

## 실행하기

```bash
uv sync --group examples
uv run uvicorn fastapi_app.main:app --app-dir examples --reload
```

<http://127.0.0.1:8000/docs>를 열어 엔드포인트를 시험해 보세요.
앱은 로컬 `examples.db` 파일에 기록하며, 이 파일은 삭제해도 됩니다.
