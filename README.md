# py_wallet-exchange-service

Read-only exchange integration service for `py_wallet`. It collects non-zero Binance
Spot balances through the signed `GET /api/v3/account` USER_DATA endpoint, persists
immutable snapshot runs in service-owned tables, and exposes them only through a
token-protected internal API. It does not implement order or transfer endpoints.

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

Generate `INTERNAL_API_TOKEN` locally instead of using the example placeholder:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The service exposes three health endpoints:

- `GET /health/live` checks that the application process is running.
- `GET /health/ready` checks the PostgreSQL connection and returns `503` when it is unavailable.
- `GET /health` is a compatibility alias for the readiness probe.

## Internal exchange API

Every internal request requires `X-Internal-Token` with the configured
`INTERNAL_API_TOKEN` value.

Collect and persist a Binance snapshot for one py_wallet user:

```bash
curl -fsS -X POST http://127.0.0.1:8002/internal/exchange-snapshots/binance \
  -H "X-Internal-Token: ${INTERNAL_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1}'
```

Read the latest successful snapshot without calling Binance again:

```bash
curl -fsS "http://127.0.0.1:8002/internal/exchange-snapshots/latest?user_id=1" \
  -H "X-Internal-Token: ${INTERNAL_API_TOKEN}"
```

The service stores `exchange_snapshot_runs` and `exchange_balances` and never stores
the Binance API key or secret. Failed collections retain only a bounded error code;
provider messages and credentials are not exposed through the API.

## Binance configuration

- `BINANCE_BASE_URL` defaults to `https://api.binance.com`.
- `BINANCE_API_KEY` and `BINANCE_API_SECRET` are required only when collecting.
- `BINANCE_TIMEOUT_SECONDS` defaults to `10`.
- `BINANCE_RECV_WINDOW_MS` defaults to Binance's recommended `5000` and cannot exceed
  `60000`.

Use a Binance key restricted to read-only account access, keep trading and withdrawals
disabled, and apply an IP allowlist when available. Credentials belong in the runtime
secret store and must never be committed. The connector signs only the official
[Account information endpoint](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#account-information-user_data)
with HMAC-SHA256 and requests `omitZeroBalances=true`.

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
  -e INTERNAL_API_TOKEN="${INTERNAL_API_TOKEN}" \
  -e BINANCE_API_KEY="${BINANCE_API_KEY}" \
  -e BINANCE_API_SECRET="${BINANCE_API_SECRET}" \
  py-wallet-exchange-service:dev
```

The component version is stored in both `VERSION` and `pyproject.toml`; release tags
must match both values.
