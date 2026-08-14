# py_wallet-exchange-service

Read-only exchange integration service for `py_wallet`. The initial scaffold provides
the FastAPI application, database migrations, health probes, local tooling, and a
container image. Exchange credentials and the Binance connector are intentionally not
part of this change.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 16+

## Local setup

```bash
cp .env.example .env
uv sync --frozen --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

The service exposes three health endpoints:

- `GET /health/live` checks that the application process is running.
- `GET /health/ready` checks the PostgreSQL connection and returns `503` when it is unavailable.
- `GET /health` is a compatibility alias for the readiness probe.

## Quality checks

```bash
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -v --tb=short
```

Run migrations against a configured PostgreSQL database:

```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

## Container

```bash
docker build -t py-wallet-exchange-service:dev .
docker run --rm -p 8002:8002 \
  -e DATABASE_URL=postgresql+psycopg://wallet:wallet@host.docker.internal:5432/wallet \
  py-wallet-exchange-service:dev
```

The component version is stored in both `VERSION` and `pyproject.toml`; release tags
must match both values.
