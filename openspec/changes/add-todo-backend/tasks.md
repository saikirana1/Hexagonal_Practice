## 1. Project scaffold and toolchain

- [ ] 1.1 Delete the empty misspelled `backed/` directory and create `backend/` as the backend project root
- [ ] 1.2 Initialise `backend/pyproject.toml` with `uv` (Python `>=3.12`) and runtime deps: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `pyjwt`, `pwdlib[argon2]`
- [ ] 1.3 Add dev deps: `pytest`, `pytest-asyncio`, `httpx`, `import-linter`, `mypy`, `ruff`; configure `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`, `pythonpath = ["src"]`)
- [ ] 1.4 Create the layer directories with `__init__.py`: `src/todo/{domain,application,adapters/inbound/http,adapters/outbound/persistence,adapters/outbound/security,adapters/outbound/system,bootstrap}`, plus `tests/` and `migrations/`
- [ ] 1.5 Add `backend/.gitignore` (`.venv`, `.env`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`)
- [ ] 1.6 Configure the `import-linter` layers contract in `pyproject.toml` per design D2: layer order `bootstrap > adapters > application > domain`, plus forbidden-module contracts banning `fastapi`, `sqlmodel`, `sqlalchemy`, `jwt`, `pwdlib`, `pydantic_settings` from `todo.domain` and `todo.application`
- [ ] 1.7 Add `backend/README.md` documenting the dependency rule, the directory map, and how to run the app, migrations, and tests

## 2. Domain layer (pure Python, no framework imports)

- [ ] 2.1 Add `domain/errors.py`: `DomainError` base plus `DomainValidationError`, `EmailAlreadyRegisteredError`, `InvalidCredentialsError`, `InvalidTokenError`, `TokenExpiredError`, `TodoNotFoundError`
- [ ] 2.2 Add `domain/value_objects.py`: `UserId`/`TodoId` (UUID newtypes) and an `Email` value object that trims and lower-cases on construction and rejects malformed addresses with `DomainValidationError`
- [ ] 2.3 Add `domain/user.py`: `User` dataclass (`id`, `email`, `password_hash`, `created_at`) with a `register()` factory taking id, email, hash, and creation time
- [ ] 2.4 Add `domain/todo.py`: `TodoStatus` (`todo`/`in_progress`/`done`) and `TodoPriority` (`low`/`medium`/`high`) enums, and a `Todo` dataclass (`id`, `owner_id`, `title`, `description`, `status`, `priority`, `due_date`, `created_at`, `updated_at`, `completed_at`)
- [ ] 2.5 Implement `Todo.create()` applying the spec defaults: status `todo`, priority `medium`, trimmed title, `updated_at == created_at`, no `completed_at`
- [ ] 2.6 Implement title/description invariants: trimmed title must be 1–200 chars, description at most 2000 chars, violations raise `DomainValidationError`
- [ ] 2.7 Implement `Todo.change_status(new_status, now)`: any-to-any transition, sets `completed_at` on entering `done`, clears it on leaving `done`, refreshes `updated_at`
- [ ] 2.8 Implement `Todo.update(...)` for partial edits of title/description/priority/due_date that refreshes `updated_at` only when a field actually changes, and reject naive (tz-less) datetimes at construction
- [ ] 2.9 Add `domain/ports.py` with `Protocol` definitions speaking domain types only: `UserRepository`, `TodoRepository` (every read/write takes a required `owner_id`), `PasswordHasher`, `TokenService`, `Clock`, `IdGenerator`
- [ ] 2.10 Add `domain/todo_query.py`: a `TodoQuery` value object carrying status/priority/due-range/search filters, sort field, sort direction, limit, and offset, validating limit `1..100` and offset `>= 0`

## 3. Domain tests

- [ ] 3.1 Test `Email` normalisation (case-folding, trimming) and rejection of malformed addresses
- [ ] 3.2 Test `Todo.create()` defaults, title trimming, and rejection of blank/oversized title and oversized description
- [ ] 3.3 Test every status transition including completion, reopening (clears `completed_at`), and `todo → done → in_progress`
- [ ] 3.4 Test that `Todo.update()` advances `updated_at`, leaves `created_at` untouched, and that a no-op update leaves the entity unchanged
- [ ] 3.5 Test `TodoQuery` validation bounds for limit and offset
- [ ] 3.6 Confirm this whole test module runs with no database, no fixtures, and no framework imports

## 4. Application layer

- [ ] 4.1 Add `application/dto.py`: frozen command dataclasses (`RegisterUserCommand`, `LoginCommand`, `CreateTodoCommand`, `UpdateTodoCommand`, `ChangeTodoStatusCommand`, `DeleteTodoCommand`, `ListTodosQuery`) and view dataclasses (`UserView`, `TodoView`, `TodoPageView`, `AccessTokenView`)
- [ ] 4.2 Add an `UNSET` sentinel used by `UpdateTodoCommand` so "field omitted" is distinguishable from "field explicitly set to null" (design D11)
- [ ] 4.3 Add `application/unit_of_work.py`: `UnitOfWork` protocol as an async context manager exposing `users`, `todos`, `commit()`, and `rollback()`
- [ ] 4.4 Implement `RegisterUser` use case: normalise email, reject a duplicate with `EmailAlreadyRegisteredError`, hash the password, persist, return `UserView`
- [ ] 4.5 Implement `AuthenticateUser` use case: look up by normalised email, verify the hash against a dummy hash when the user is absent (constant-time-ish, design risk note), raise `InvalidCredentialsError` identically for unknown-email and wrong-password, issue a token
- [ ] 4.6 Implement `GetCurrentUser` use case returning the acting user's `UserView`
- [ ] 4.7 Implement `CreateTodo` use case taking the owner from the authenticated actor only, using injected `IdGenerator` and `Clock`
- [ ] 4.8 Implement `GetTodo` use case: fetch scoped by `(todo_id, owner_id)`, raise `TodoNotFoundError` when the repository returns `None`
- [ ] 4.9 Implement `ListTodos` use case returning items plus total count, applied limit, and applied offset
- [ ] 4.10 Implement `UpdateTodo` use case applying only supplied fields (honouring `UNSET` vs explicit null) and persisting the mutated entity
- [ ] 4.11 Implement `ChangeTodoStatus` use case delegating to `Todo.change_status()`
- [ ] 4.12 Implement `DeleteTodo` use case: owner-scoped delete, `TodoNotFoundError` when nothing was deleted

## 5. Application tests against in-memory fakes

- [ ] 5.1 Build `tests/fakes/`: dict-backed `InMemoryUserRepository` and `InMemoryTodoRepository` (enforcing owner scoping and implementing filter/sort/paginate), `FrozenClock`, `TickingClock`, `SequentialIdGenerator`, `FakePasswordHasher`, `FakeTokenService`, and a fake `UnitOfWork`
- [ ] 5.2 Test `RegisterUser`: success, duplicate email in differing case rejected, password never stored in plaintext
- [ ] 5.3 Test `AuthenticateUser`: success, wrong password, unknown email — asserting the last two raise the identical error
- [ ] 5.4 Test `CreateTodo` ignores any owner supplied in the command payload and always uses the actor
- [ ] 5.5 Test owner isolation for get, update, status change, and delete — each raises `TodoNotFoundError` for a non-owner and leaves the target untouched
- [ ] 5.6 Test `ListTodos` filters (status, priority, due-date range inclusive, case-insensitive title search), each sort field in both directions, id tie-breaking, and pagination totals
- [ ] 5.7 Test `UpdateTodo` partial semantics: untouched fields preserved, explicit null clears the due date, `updated_at` advances via `TickingClock`, empty update is a no-op success

## 6. Outbound adapters

- [ ] 6.1 Add `adapters/outbound/persistence/models.py`: `UserRecord` and `TodoRecord` SQLModel tables per design D9 (UUID PKs, `TIMESTAMPTZ` columns, enums as `VARCHAR` with `CHECK` constraints, `owner_id` FK with `ON DELETE CASCADE`)
- [ ] 6.2 Declare indexes on the record models: unique index on `lower(email)`, and `(owner_id, created_at desc)`, `(owner_id, status)`, `(owner_id, due_date)` on todos
- [ ] 6.3 Add `adapters/outbound/persistence/mappers.py` with `to_domain()` / `to_record()` for both aggregates, plus round-trip tests
- [ ] 6.4 Implement `SqlAlchemyUserRepository` against `AsyncSession` (get by normalised email, get by id, add)
- [ ] 6.5 Implement `SqlAlchemyTodoRepository`: owner-scoped get/add/update/delete, and a `list()` translating `TodoQuery` into `WHERE`/`ILIKE`/`ORDER BY` (with id tie-break)/`LIMIT`/`OFFSET` plus a matching total-count query
- [ ] 6.6 Implement `SqlAlchemyUnitOfWork` over `async_sessionmaker`, exposing both repositories and committing on clean exit / rolling back on exception
- [ ] 6.7 Implement `Argon2PasswordHasher` (`pwdlib`) with `hash`/`verify` executed via `anyio.to_thread.run_sync` so the event loop is not blocked (design risk note)
- [ ] 6.8 Implement `JwtTokenService` (PyJWT): issue with `sub`, `iat`, `exp`; decode mapping expiry to `TokenExpiredError` and any other decode failure to `InvalidTokenError`
- [ ] 6.9 Implement `SystemClock` (UTC-aware) and `Uuid4IdGenerator` in `adapters/outbound/system/`

## 7. Bootstrap and configuration

- [ ] 7.1 Add `bootstrap/settings.py` with `pydantic-settings`: `database_url` and `jwt_secret` as `SecretStr`, `jwt_algorithm`, `access_token_ttl_seconds`, `environment`, `log_level`; fail startup with a message naming any missing required setting
- [ ] 7.2 Normalise the Neon URL in settings: force the `postgresql+asyncpg` scheme and strip libpq-only query params such as `sslmode`/`channel_binding` that asyncpg rejects
- [ ] 7.3 Add `bootstrap/db.py`: async engine with `pool_pre_ping=True`, `NullPool`, and `connect_args={"ssl": "require", "statement_cache_size": 0, "prepared_statement_cache_size": 0}` for the Neon pooled endpoint (design D8); plus the `async_sessionmaker`
- [ ] 7.4 Add `bootstrap/container.py`: construct concrete adapters and expose FastAPI dependency providers building each use case — the only module in the codebase naming concrete adapter classes
- [ ] 7.5 Add `bootstrap/app.py` with a `create_app()` factory registering routers, exception handlers, and a lifespan that opens a warm-up connection and disposes the engine on shutdown
- [ ] 7.6 Add `backend/.env.example` documenting every setting, including which environments use the Neon pooled versus direct endpoint, and a note that migrations run against the direct endpoint
- [ ] 7.7 Add structured startup logging that reports the environment and masks the database password and JWT secret

## 8. Inbound HTTP adapter

- [ ] 8.1 Add `adapters/inbound/http/schemas.py`: Pydantic request/response models distinct from the domain (`RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `CreateTodoRequest`, `UpdateTodoRequest`, `TodoResponse`, `TodoPageResponse`) with declared constraints (title 1–200, description ≤2000, limit 1–100, offset ≥0)
- [ ] 8.2 Model `UpdateTodoRequest` so an omitted field and an explicit `null` are distinguishable, and map both onto the application `UNSET` sentinel
- [ ] 8.3 Add `adapters/inbound/http/errors.py`: the error envelope model and FastAPI exception handlers implementing the full error→status→code table in design D11, including a `RequestValidationError` handler emitting `422 VALIDATION_ERROR` with per-field `details`
- [ ] 8.4 Add a catch-all handler returning `500 INTERNAL_ERROR` that logs the exception with a correlation id and leaks no stack trace, SQL, or connection details
- [ ] 8.5 Add `adapters/inbound/http/dependencies.py`: bearer-token extraction and actor resolution, returning `401 NOT_AUTHENTICATED` for a missing or malformed header and `401 INVALID_TOKEN` when the token's subject no longer exists
- [ ] 8.6 Add the auth router: `POST /api/v1/auth/register` (201), `POST /api/v1/auth/login` (200), `GET /api/v1/auth/me` (200)
- [ ] 8.7 Add the todos router: `POST /api/v1/todos` (201), `GET /api/v1/todos` (200, filters/sort/pagination as query params), `GET /api/v1/todos/{todo_id}` (200), `PATCH /api/v1/todos/{todo_id}` (200), `DELETE /api/v1/todos/{todo_id}` (204)
- [ ] 8.8 Add the health router: unauthenticated `GET /health` outside the version prefix, returning `200 ok/ok` or `503 degraded/error` based on a database connectivity check
- [ ] 8.9 Confirm no router module imports a repository, a session, or a SQLModel record — routers touch only schemas, dependencies, and use cases

## 9. Database migrations

- [ ] 9.1 Initialise Alembic in `backend/migrations/` using the **async** template; point `target_metadata` at SQLModel's metadata and import the record models so autogenerate sees them
- [ ] 9.2 Wire `env.py` to read the database URL from `Settings` rather than from `alembic.ini`, so there is one source of configuration
- [ ] 9.3 Generate and hand-review the initial migration creating `users` and `todos` with all constraints, the `lower(email)` unique index, the `ON DELETE CASCADE` FK, the enum `CHECK` constraints, and the composite indexes
- [ ] 9.4 Verify `alembic upgrade head` followed by `alembic downgrade base` runs clean against a real Postgres
- [ ] 9.5 Add a test asserting `alembic check` (autogenerate diff) reports no drift between the record models and the migration history

## 10. Integration tests over HTTP and Postgres

- [ ] 10.1 Add `tests/conftest.py`: require `TEST_DATABASE_URL` and fail loudly if unset (never fall back to `DATABASE_URL`), apply migrations once per session, and wrap each test in a rolled-back transaction
- [ ] 10.2 Add an ASGI client fixture over `create_app()` using `httpx.ASGITransport`, plus a helper that registers a user and returns an authorised client
- [ ] 10.3 Test the auth flow end to end: register 201, duplicate email 409 `EMAIL_ALREADY_REGISTERED` (including differing case), malformed email 422, weak password 422, login 200 with token/type/expiry, wrong password and unknown email both 401 `INVALID_CREDENTIALS` with identical messages
- [ ] 10.4 Test protected access: missing header 401 `NOT_AUTHENTICATED`, malformed header 401 `NOT_AUTHENTICATED`, tampered token 401 `INVALID_TOKEN`, expired token 401 `TOKEN_EXPIRED`, token for a deleted user 401 `INVALID_TOKEN`
- [ ] 10.5 Test the todo lifecycle over HTTP: create 201, get 200, patch 200, status change through `done` and back, delete 204 then get 404
- [ ] 10.6 Test cross-user isolation over HTTP with two registered users: get/patch/delete of the other user's todo all return 404 `TODO_NOT_FOUND` and leave the todo intact, and listing never returns the other user's rows
- [ ] 10.7 Test listing against seeded data: default 20-item page ordered by `created_at` desc, each filter, case-insensitive search, each sort field and direction, pagination totals, bounds rejection (422), and the empty result case
- [ ] 10.8 Test the error envelope shape on 404/409/422/500 responses and assert no response body exposes `password_hash` or internal details
- [ ] 10.9 Test `GET /health` returns 200 `ok`/`ok` against a live database, and 503 `degraded`/`error` when the connectivity check is made to fail
- [ ] 10.10 Test that deleting a user row cascades away that user's todos

## 11. Verification and handoff

- [ ] 11.1 Run `lint-imports` and confirm the layer contract passes with zero violations
- [ ] 11.2 Run `ruff check`, `ruff format --check`, and `mypy src` clean
- [ ] 11.3 Run the full `pytest` suite green against a real Postgres and record the coverage of each spec requirement
- [ ] 11.4 Cross-check every requirement in `specs/api-foundation`, `specs/user-auth`, and `specs/todo-management` against a test that exercises it, and note any gaps
- [ ] 11.5 Boot the app against Neon and manually smoke-test register → login → create → list → update → delete, confirming `/health` and the OpenAPI docs at `/docs`
- [ ] 11.6 Verify the generated OpenAPI schema is complete enough to serve as the UI contract for the follow-up change
