## Todo API

A create/read Todo API using FastAPI, SQLModel, PostgreSQL (including Neon), and Alembic.
The application core is function-based: domain validation is pure and database/time/ID effects are passed into use-case functions.

### Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync --all-groups
cp .env.example .env
```

Set `DATABASE_URL` to your Neon pooled or direct PostgreSQL URL. The standard Neon URL format is supported.

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### API

- `POST /api/v1/todos` creates a Todo.
- `GET /api/v1/todos` returns Todos, newest first.
- `GET /health` returns application health.

```json
{"title": "Buy milk", "description": "Two litres"}
```

### Tests

```bash
uv run pytest
```
