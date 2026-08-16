## Context

Greenfield repository — no application code exists, so there is no legacy structure to accommodate and no migration from an existing system. See `proposal.md` § Why for motivation, and the three delta specs under `specs/` for the behaviour being contracted.

Constraints that shape this design:

- **Strict hexagonal architecture is a hard requirement**, not a suggestion. The value of this repo (`Hexagonal_Practice`) is the structure itself, so the layering rule is enforced mechanically in CI, not left to discipline.
- **Neon Postgres** is serverless: it auto-suspends idle compute (causing a multi-second cold start on the next connection), and its pooled endpoint sits behind PgBouncer in transaction mode. Both facts constrain connection-pool and driver configuration.
- **SQLModel + Alembic** are prescribed. SQLModel's table classes are SQLAlchemy models with Pydantic behaviour bolted on — which makes them tempting to use as domain entities. This design deliberately refuses that, because it would invert the dependency rule.
- The API must be a stable contract for a UI that will be built as a **separate, later change**.
- A sibling project (`expenses/backend`) established the house toolchain: `uv`, FastAPI, SQLModel, Alembic, `pwdlib[argon2]`, `pyjwt`, `pytest`. This design keeps that toolchain and changes only the architecture.

## Goals / Non-Goals

**Goals:**

- A dependency rule that points strictly inward, is stated in one place, and fails the build when violated.
- A domain layer that is pure Python: no FastAPI, no SQLModel, no SQLAlchemy, no `datetime.now()`, no `uuid4()` called inline — testable with zero I/O and zero fixtures.
- Ports defined by and owned by the inside (domain/application); adapters on the outside implement them.
- One composition root that is the only place where concrete adapters are named.
- Persistence and transaction boundaries that are explicit and per-use-case, not implicit per-request magic.
- A test pyramid whose shape follows the architecture: many fast domain tests, use-case tests against in-memory fakes, and a thin band of HTTP+Postgres integration tests.

**Non-Goals:**

- CQRS, event sourcing, a domain event bus, or an outbox. Hexagonal does not require them, and they would obscure the pattern being practised.
- A generic `Repository[T]` base class or any premature abstraction over ports.
- Multi-tenancy beyond per-user ownership; roles, permissions, or sharing.
- Caching, background workers, rate limiting, observability stack, containerisation, or deployment. Later changes.
- Refresh tokens, token revocation/denylist, password reset, email verification (stated as out of scope in the proposal; the token port is nonetheless shaped so these can be added without touching the domain).

## Decisions

### D1. Four layers, one inward-pointing dependency rule

```
backend/
  src/todo/
    domain/         # entities, value objects, domain errors, PORT interfaces
    application/    # use cases (interactors), DTOs, unit-of-work contract
    adapters/
      inbound/http/     # FastAPI routers, request/response schemas, error mapper
      outbound/persistence/   # SQLModel tables, mappers, repository implementations
      outbound/security/      # argon2 hasher, PyJWT token service
      outbound/system/        # system clock, uuid id generator
    bootstrap/      # settings, engine/session factory, DI container, app factory
  migrations/       # alembic
  tests/
```

Allowed import directions: `bootstrap → adapters → application → domain`. Nothing imports outward; `domain` imports nothing from the project but itself.

**Why this shape:** the two most common ways a hexagonal codebase rots are (a) the ORM model leaking upward as the domain entity, and (b) a use case importing a concrete adapter "just this once". Splitting `adapters/inbound` from `adapters/outbound` also makes the driving/driven distinction visible in the tree instead of only in a diagram.

**Alternatives considered:**
- *Clean Architecture's four rings with an explicit `interface_adapters` layer* — same dependency rule, more ceremony, and the extra ring adds nothing here.
- *Package-by-feature at the top level* (`src/todo/auth/{domain,application,adapters}`) — better for very large systems and easier to extract into services later; rejected because with two aggregates it multiplies directories, and it makes the layering harder to see, which is the point of this repo. Feature grouping still happens *within* each layer (`domain/todo.py`, `domain/user.py`).

### D2. The dependency rule is enforced by a test, not by convention

An `import-linter` contract (config in `pyproject.toml`, run in CI and in the test suite) declares the layer order and forbids `domain`/`application` from importing `fastapi`, `sqlmodel`, `sqlalchemy`, `jwt`, `pwdlib`, or `pydantic_settings`.

**Why:** "we all agree to keep the domain clean" has a half-life measured in weeks. A failing check is what makes this architecture real. `import-linter` is chosen over a hand-rolled AST test because layer contracts are declarative and the failure output names the offending import chain.

**Trade-off:** one more dev dependency and one more CI gate. Accepted — it is the cheapest possible enforcement.

### D3. Domain entities are plain `@dataclass`, never SQLModel

`domain/todo.py` defines a `Todo` dataclass plus `TodoStatus`/`TodoPriority` enums and a `TodoTitle`-style validation at construction. Business rules live as methods on the entity: `Todo.change_status()` sets/clears `completed_at`, `Todo.rename()` validates and touches `updated_at`.

**Why:** if `Todo` were a SQLModel table class, the domain would import SQLAlchemy, and the dependency rule would be broken at the innermost ring — the failure mode this whole exercise exists to avoid. Dataclasses also mean domain tests need no database, no metadata registry, and no fixtures.

**Alternatives considered:**
- *SQLModel classes as domain entities* (the classic "SQLModel lets you use one model everywhere" pitch) — genuinely less code, and correct for a CRUD service. Rejected outright here: it is the exact inversion this change is meant to demonstrate the alternative to.
- *Pydantic `BaseModel` for entities* — gives free validation, but drags Pydantic into the domain and encourages validation-by-serialization rather than invariants-by-construction. Pydantic stays in the inbound adapter where it belongs.

**Cost, stated plainly:** an explicit mapper between `Todo` and `TodoRecord`. That duplication is the price of the boundary, and it is paid in one file per aggregate.

### D4. Ports are `typing.Protocol` in the domain; adapters implement them structurally

`domain/ports.py` (or `domain/ports/`) declares `UserRepository`, `TodoRepository`, `PasswordHasher`, `TokenService`, `Clock`, `IdGenerator` as `Protocol` classes. Repository ports speak *domain types only* — `save(todo: Todo) -> None`, `get(todo_id: TodoId, owner_id: UserId) -> Todo | None`.

**Why `Protocol` over `abc.ABC`:** the adapter does not import the port to inherit from it, so even the *import* direction stays inward-only; fakes in tests need no base class; and structural typing is checked statically by mypy rather than at runtime. (Adapters may still annotate themselves against the protocol for editor support — that import is inward, hence legal.)

**Ownership rule:** ports are named for what the *inside* needs (`PasswordHasher`), not for what the outside provides (`Argon2Service`).

### D5. Owner scoping is a repository-port parameter, not a filter the caller may forget

Every todo-fetching port method takes `owner_id` as a required argument. There is no `get_by_id(todo_id)` overload. The SQL adapter always emits `WHERE id = :id AND owner_id = :owner`, so a missing scope is a type error at the call site rather than a data leak at runtime.

**Why:** the isolation requirement in `specs/todo-management` ("answered exactly as if the todo did not exist") is the one rule where a single forgotten `WHERE` clause is a security bug. Encoding it in the port signature makes the safe path the only path. The use case maps `None` → `TodoNotFoundError` uniformly, which is also what produces the 404-not-403 behaviour the spec requires.

**Alternative considered:** fetch-then-authorize in the use case (`if todo.owner_id != actor.id: raise`). Equally correct when written correctly, but it is one `if` away from being wrong, and it fetches other users' rows into memory.

### D6. One use case per class, invoked as `execute()`

`application/use_cases/create_todo.py` → `CreateTodo` with constructor-injected ports and `async def execute(self, command: CreateTodoCommand) -> TodoView`. Commands and views are frozen dataclasses in `application/dto.py`.

**Why:** each use case declares exactly the ports it needs, which keeps test fakes minimal and makes the dependency graph readable. A single fat `TodoService` would depend on the union of everything and drift back into a service layer.

**Trade-off:** more files (~10 use-case classes). Accepted; each is 15–30 lines and trivially testable.

### D7. Transactions: an explicit `UnitOfWork` owned by the application layer

`application/unit_of_work.py` declares a `UnitOfWork` protocol — an async context manager exposing the repositories and `commit()`/`rollback()`. The SQLAlchemy adapter implements it over `AsyncSession`. The inbound adapter opens **one unit of work per request** and hands it to the use case; commit happens on clean exit, rollback on any exception.

**Why:** with repositories alone, "who commits?" is unanswered, and the usual answer — a FastAPI dependency that commits after the response — hides the transaction boundary from the code that owns the invariants. Making the boundary explicit also means a future multi-repository use case is atomic by construction.

**Alternative considered:** `session.commit()` inside each repository method. Simplest, and fine for single-aggregate writes; rejected because it makes atomicity across aggregates impossible without refactoring every adapter.

### D8. Async stack with `asyncpg`, and Neon-specific engine configuration

Driver: `postgresql+asyncpg`. Engine created once in `bootstrap/db.py` with:

- `pool_pre_ping=True` — Neon auto-suspends idle compute and drops connections; without this the first request after idling fails.
- `NullPool` when connecting through Neon's **pooled** endpoint (PgBouncer, transaction mode), plus `statement_cache_size=0` and `prepared_statement_cache_size=0` in `connect_args`. asyncpg prepares statements by default; PgBouncer in transaction mode does not keep them across transactions, which surfaces as intermittent `InvalidSQLStatementNameError`. This is the single most common Neon+asyncpg failure and is configured deliberately rather than discovered in production.
- TLS is required by Neon. asyncpg does **not** understand libpq's `?sslmode=require` query parameter (that is a psycopg spelling); the URL is normalised in settings and SSL is passed via `connect_args={"ssl": "require"}`.

**Alternatives considered:**
- *Sync `psycopg[binary]` + `Session`* — matches the sibling `expenses/backend` exactly and is simpler to reason about. Rejected per the decision recorded at proposal time: async is the better fit for Neon's latency profile and FastAPI's concurrency model, and mixing sync DB calls into async routes silently ties up the event loop.
- *`psycopg` v3 async* — a valid alternative that handles PgBouncer more gracefully; asyncpg chosen for maturity with SQLAlchemy's async dialect and better throughput. If PgBouncer friction proves worse than expected, swapping is a one-line dialect change plus `connect_args`, isolated to `bootstrap/db.py` — precisely the kind of change this architecture is supposed to localise.

### D9. Persistence models are separate `TodoRecord`/`UserRecord` SQLModel tables with explicit mappers

`adapters/outbound/persistence/models.py` holds the SQLModel table classes; `mappers.py` holds `to_domain()` / `to_record()`. Alembic's `target_metadata` points at SQLModel's metadata, which sees only these record classes.

**Why:** it is what D3 implies, and it lets the storage schema evolve (indexes, denormalised columns, column renames) without touching the domain.

**Schema notes:** `users(id uuid pk, email citext/varchar unique, password_hash, created_at)` with a **unique index on `lower(email)`** to enforce the case-insensitive uniqueness the spec requires at the database level, not just in application code. `todos(id uuid pk, owner_id uuid fk → users.id ON DELETE CASCADE, title, description, status, priority, due_date, created_at, updated_at, completed_at)` with a composite index on `(owner_id, created_at desc)` to serve the default listing, and supporting indexes on `(owner_id, status)` and `(owner_id, due_date)`. `ON DELETE CASCADE` is what satisfies the "todos are removed with their owner" requirement.

**Enums stored as `VARCHAR` + `CHECK`,** not native Postgres `ENUM` types: adding a status value later is an ordinary migration rather than a `ALTER TYPE` dance, and the domain enum remains the source of truth.

**Timestamps are `TIMESTAMPTZ`, always UTC.** Naive datetimes are rejected at the boundary.

### D10. Time and identity are ports, not ambient calls

`Clock.now() -> datetime` and `IdGenerator.new_id() -> UUID` are injected. The domain never calls `datetime.now(UTC)` or `uuid4()` directly.

**Why:** the specs assert on timestamp behaviour (`updated_at` strictly increases, `completed_at` set/cleared). With an injected `FrozenClock`/`TickingClock` those become exact assertions instead of `sleep()`-and-hope. Deterministic ids make test fixtures readable.

**Trade-off:** two more constructor parameters on most use cases. Cheap, and it is the standard way to make a domain testable.

### D11. HTTP is one of several possible inbound adapters, and is kept thin

Routers do exactly four things: parse into a Pydantic request schema, resolve the actor from the bearer token, call `use_case.execute(command)`, and serialise the returned view. No business logic, no ORM access, no error string formatting.

Domain and application errors are translated by a **single exception-mapping layer** (`adapters/inbound/http/errors.py`) registered as FastAPI exception handlers, which emits the uniform envelope from `specs/api-foundation`:

| Error | HTTP | `error.code` |
|---|---|---|
| `EmailAlreadyRegisteredError` | 409 | `EMAIL_ALREADY_REGISTERED` |
| `InvalidCredentialsError` | 401 | `INVALID_CREDENTIALS` |
| `TokenExpiredError` | 401 | `TOKEN_EXPIRED` |
| `InvalidTokenError` | 401 | `INVALID_TOKEN` |
| missing/malformed `Authorization` | 401 | `NOT_AUTHENTICATED` |
| `TodoNotFoundError` | 404 | `TODO_NOT_FOUND` |
| `ValidationError` (Pydantic) / `DomainValidationError` | 422 | `VALIDATION_ERROR` |
| anything else | 500 | `INTERNAL_ERROR` |

**Why one mapper:** codes stay stable and exhaustive in one table, and no router can invent its own error shape. The catch-all handler logs the exception with a correlation id server-side and returns none of it to the client, satisfying the "does not leak internals" scenario.

**Partial updates and the null-vs-absent problem:** `PATCH` bodies use a sentinel (`UNSET`) so that "field omitted" and "field explicitly set to null" are distinguishable, as the spec requires for clearing a due date. The application-layer `UpdateTodoCommand` carries the same sentinel; the domain sees only concrete values.

### D12. Composition root in `bootstrap/`, hand-wired

`bootstrap/container.py` constructs settings, engine, session factory, and the concrete adapters, and exposes FastAPI dependency providers that build each use case. `bootstrap/app.py` is the `create_app()` factory (routers, exception handlers, lifespan). No DI framework.

**Why:** with ~6 ports and ~10 use cases, hand-wiring is a readable file and adds zero magic — and it makes the "only one place names concrete classes" rule obvious. `create_app()` as a factory (rather than a module-level `app`) is what lets integration tests build an app against a test database and override providers with fakes.

**Alternative considered:** `dependency-injector` or `punq`. Reasonable at larger scale; unnecessary here and it would obscure the wiring that this repo exists to demonstrate.

### D13. Settings via `pydantic-settings`, validated at startup

`bootstrap/settings.py` defines `Settings` with `database_url` (secret), `jwt_secret` (secret), `jwt_algorithm` (default `HS256`), `access_token_ttl_seconds` (default 3600), `environment`, `log_level`. Missing or empty required values abort startup with a message naming the setting; `SecretStr` keeps them out of logs and repr. `.env.example` is committed; `.env` is git-ignored.

### D14. Test strategy mirrors the layers

- **Domain tests** — pure, no fixtures, no I/O. Entity invariants and status-transition rules.
- **Use-case tests** — the use case wired to in-memory fake repositories (dict-backed), a `FrozenClock`, a `FakeIdGenerator`, and a fake hasher/token service. These are where the isolation rules and the "wrong owner ⇒ not found" behaviour are asserted, without a database.
- **HTTP integration tests** — `httpx.ASGITransport` against `create_app()` wired to a **real Postgres** (a dedicated Neon branch or a local container), migrations applied, each test in a rolled-back transaction. These cover the wire contract: status codes, the error envelope, and auth.
- **Migration test** — `alembic upgrade head` then `downgrade base` runs clean; and an autogenerate-diff check asserts the models and the migration history have not drifted apart.
- **Architecture test** — the `import-linter` contract from D2.

**Why a real Postgres rather than SQLite for integration:** the design depends on Postgres-specific behaviour (case-insensitive unique index, `ON DELETE CASCADE`, `TIMESTAMPTZ`, `ILIKE`). SQLite would pass tests that production would fail.

## Risks / Trade-offs

- **[Boilerplate fatigue]** Entity + record + mapper + port + adapter + DTO per aggregate is a lot of files for a todo app; a newcomer may see ceremony rather than architecture. → Keep the layer count at four and refuse further abstraction (no generic repository, no service locator). Document the dependency rule in `backend/README.md` with the one-paragraph "why" and let D2's linter, not review comments, police it.
- **[Domain/record drift]** A column added to `TodoRecord` without a matching domain change (or vice versa) is silently ignored by the mapper. → Mapper round-trip tests (`to_record(to_domain(r)) == r`) per aggregate, and the Alembic autogenerate-diff check in D14.
- **[Neon + PgBouncer prepared statements]** Misconfiguration surfaces as intermittent, hard-to-reproduce `InvalidSQLStatementNameError` under concurrency rather than a clean startup failure. → Configure `statement_cache_size=0` + `NullPool` from the start (D8), record which endpoint (pooled vs direct) each environment uses in `.env.example`, and run integration tests against the pooled endpoint so the configuration is exercised.
- **[Neon cold starts]** A suspended compute adds seconds to the first request and can make CI flaky. → `pool_pre_ping=True`, a generous connect timeout, and a warm-up connection in the app lifespan. Treat the first CI request as unmeasured.
- **[Async everywhere]** One accidental blocking call (a sync driver, a CPU-bound hash) stalls the event loop. Argon2 hashing is deliberately expensive and *is* CPU-bound. → Run password hashing/verification in a threadpool (`anyio.to_thread.run_sync`) inside the hasher adapter; the port stays `async`, so the domain is unaffected. The import-linter contract prevents sync DB drivers from reappearing.
- **[Timing oracle on login]** Returning early for an unknown email makes "user exists" measurable even though the message is identical. → Verify against a dummy hash when no user is found, so both paths do the same work.
- **[No refresh tokens]** Access tokens are the only credential; a leaked token is valid until it expires and cannot be revoked. → Short TTL (1 hour default), and the `TokenService` port is shaped so a denylist or refresh flow can be added behind it without touching the domain. Explicitly accepted for this change.
- **[Offset pagination]** `OFFSET` degrades on large result sets and can skip/duplicate rows when the underlying data changes between pages. → Acceptable at this scale, and the deterministic tie-break on id (required by the spec) bounds the anomaly. Keyset pagination is a later, additive change to the same port signature.
- **[Test database cost/isolation]** Integration tests need a Postgres that is not the dev database. → Use a dedicated Neon branch (cheap, disposable) for CI and support a local container via `TEST_DATABASE_URL`; fail loudly if it is unset rather than silently falling back to `DATABASE_URL`.

## Migration Plan

No data migration — the system does not yet exist. Deployment sequencing for the first release:

1. Provision the Neon project and a `dev` branch; record the **direct** and **pooled** connection strings.
2. Create `.env` from `.env.example`; generate a strong `JWT_SECRET`.
3. Run `alembic upgrade head` against the **direct** (non-pooled) endpoint — DDL through PgBouncer transaction pooling is unreliable.
4. Start the app against the **pooled** endpoint; confirm `GET /health` reports `ok`/`ok`.
5. Smoke-test register → login → create todo → list → update → delete.

**Rollback:** every migration ships with a working `downgrade`; `alembic downgrade -1` reverts the schema step. Because this is the initial release, the practical rollback is `alembic downgrade base` plus redeploying nothing. Neon branch snapshots provide a second safety net.

**Removal of `backed/`:** the directory is empty and untracked-by-content; deleting it carries no risk.

## Open Questions

- Whether to expose account deletion (`DELETE /api/v1/users/me`) in this change. The `ON DELETE CASCADE` behaviour is specified and will be tested at the repository level regardless; adding the endpoint later is purely additive and changes no existing contract.
- Whether CI's integration tests run against a dedicated Neon branch or a containerised Postgres. Both satisfy D14; the choice affects CI configuration only and can be settled when CI is set up.
