# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Add a signed, read-only Binance Spot balance connector and token-protected internal API.
- Persist exchange snapshot runs and non-zero balances in exchange-service-owned tables.
- Scaffold the FastAPI exchange service with PostgreSQL-backed readiness checks.
- Add uv, Ruff, mypy, pytest, Alembic, Docker, and pull-request CI configuration.
