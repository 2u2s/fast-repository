# FastAPI integration

`fast-repository` is built for FastAPI: a repository takes just a SQLAlchemy session,
so it drops straight into `Depends`. This guide walks through the example app in
[`examples/fastapi_app/`](../../examples/fastapi_app), which is split by responsibility
so each piece of the integration is easy to find.

## Project layout

| File              | Responsibility                                                      |
|-------------------|---------------------------------------------------------------------|
| `database.py`     | Engine, session maker, `lifespan`, and the `get_session` dependency |
| `dependencies.py` | Builds the repository and exposes it as the abstract type           |
| `dtos.py`         | Pydantic request/response models and the list-query parameters      |
| `routers.py`      | The `/users` endpoints                                              |
| `main.py`         | Assembles the app and calls `add_pagination`                        |

The entity and repositories live in the shared [`examples/models.py`](../../examples/models.py);
the enum used for `User.status` lives in [`examples/enums.py`](../../examples/enums.py).

## Injecting the repository

The repository takes a session in its constructor, so a dependency function can build a
fresh one per request. Return it typed as the *abstract* interface, so your routes
depend on that interface rather than on the concrete SQLAlchemy implementation:

```python
# dependencies.py
def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AbstractUserRepository:
    return UserRepository(session)


UserRepo = Annotated[AbstractUserRepository, Depends(get_user_repository)]
```

A handler then only needs the `UserRepo` alias:

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

## Updating is just saving

There is no separate update method.
Load the entity, apply the fields the client sent, and `save` it again:

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

## Filtering and ordering from query parameters

`find_all_paginated` takes the same keyword filters as `find_all`: a bare
`column=value` is equality, and a `column__operator` suffix applies an operator
such as `ge`. Map your query parameters onto those filters:

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

`order_by` takes raw SQLAlchemy order terms, so the example turns an `order` value
like `-age` into `User.age.desc()`. The runnable code factors this into a small
`_order_by` helper. See [Filtering](filtering.md) for the full operator list.

## Pagination

`find_all_paginated` returns a `fastapi_pagination.Page`. Inside a request you do
not pass `params` — `add_pagination(app)` lets fastapi-pagination read `?page=`
and `?size=` from the query string automatically:

```python
# main.py
app = FastAPI(lifespan=lifespan)
app.include_router(router)
add_pagination(app)
```

Declare the response as `Page[UserOut]` and the page metadata (`total`, `page`,`size`)
is filled in for you.

## Error handling

`find` returns `None` when nothing matches; turn that into a 404:

```python
user = await repo.find(user_id)
if user is None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="user not found",
    )
```

## Running it

```bash
uv sync --group examples
uv run uvicorn fastapi_app.main:app --app-dir examples --reload
```

Open <http://127.0.0.1:8000/docs> to try the endpoints. The app writes to a local
`examples.db` file, which is safe to delete.
