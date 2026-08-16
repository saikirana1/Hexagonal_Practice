## Why

This repository is an empty scaffold (`backed/`, `ui/`) with no application code. We need a production-grade Todo backend that is worth building on: a real HTTP API, real persistence on Neon Postgres, and a strict Hexagonal (ports & adapters) structure so the domain rules stay independent of FastAPI, SQLModel, and the database. Building the backend first gives the UI (planned as a separate, later change) a stable contract to consume.

## What Changes

- Establish the backend project at `backend/` (the existing empty `backed/` folder is a typo and is replaced), managed with `uv`, Python 3.12+, FastAPI, SQLModel, Alembic, and async Postgres access against Neon.
- Enforce a strict hexagonal layout with an inward-only dependency rule: `domain` (entities, value objects, domain errors, port interfaces) ← `application` (use cases) ← `adapters` (inbound HTTP, outbound persistence/security/clock) ← `bootstrap` (composition root, settings, DI wiring). The domain and application layers import no framework or driver code.
- Add user accounts with registration and login: argon2 password hashing, JWT access tokens, and an authenticated principal resolved per request.
- Add todo management scoped to the authenticated owner: create, read, update, delete, plus status transitions, priority, due date, and timestamps. List supports filtering, sorting, and pagination.
- Enforce per-user isolation: a todo is only ever readable or mutable by its owner; cross-owner access is indistinguishable from "not found".
- Add an API foundation: versioned routes under `/api/v1`, a uniform JSON error envelope mapping domain errors to HTTP status codes, request/response schemas separate from domain models, and a health endpoint.
- Add Alembic migrations for `users` and `todos`, configured for the async engine, with the Neon connection string supplied by environment configuration.
- Add an automated test suite covering domain rules in isolation (no I/O), use cases against in-memory fake adapters, and HTTP integration tests against a real Postgres schema.

## Capabilities

### New Capabilities
- `api-foundation`: Versioned HTTP surface, uniform error envelope, request validation behavior, and health/readiness reporting for the backend service.
- `user-auth`: User registration, credential verification, access-token issuance, and resolution of the authenticated principal on protected requests.
- `todo-management`: Owner-scoped todo lifecycle — creation, retrieval, listing with filter/sort/pagination, attribute updates, status transitions, and deletion.

### Modified Capabilities
<!-- None. This is the first change in the repository; no existing specs. -->

## Impact

- **New code**: `backend/` project root containing `src/todo/domain`, `src/todo/application`, `src/todo/adapters`, `src/todo/bootstrap`, plus `migrations/` (Alembic) and `tests/`.
- **Removed**: the empty, misspelled `backed/` directory.
- **APIs**: introduces `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET|POST /api/v1/todos`, `GET|PATCH|DELETE /api/v1/todos/{todo_id}`, and `GET /health`. All are new; nothing is breaking.
- **Dependencies**: `fastapi`, `uvicorn`, `sqlmodel`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `pydantic-settings`, `pyjwt`, `pwdlib[argon2]`; dev: `pytest`, `pytest-asyncio`, `httpx`.
- **Infrastructure**: requires a Neon Postgres project and a `DATABASE_URL` (plus a separate test database or schema for integration tests) and a `JWT_SECRET`, both supplied via environment / `.env`.
- **Out of scope**: the UI (a later change), refresh tokens / token revocation, password reset, email verification, and deployment packaging (Docker/Lambda).
