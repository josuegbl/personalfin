---
name: "BankFinances Backend"
description: "Use when modifying the FastAPI, Python, SQLAlchemy services, routers, schemas, sync adapters, scheduled jobs, or backend scripts in backend/."
applyTo: ["backend/**/*.py", "backend/requirements.txt"]
---

# Backend Instructions

- Run backend commands from `backend/` so `.env`, `alembic.ini`, and application imports resolve correctly. Use the repository virtual environment when available: `source .venv/bin/activate`.
- Keep the boundary clear: routers handle HTTP and dependency injection, services contain business logic, models define persistence, and Pydantic schemas define API contracts. Do not move database logic into frontend code or duplicate API parsing outside `backend/app/api/` and `backend/app/services/`.
- All API routes are under `/api/v1`. Preserve established Spanish field names and compatibility quirks unless the API contract is intentionally versioned. In particular, treat `excluir_pasthrough` as an existing public parameter.
- Sync adapters implement `SourceAdapter` in `backend/app/services/sync/base.py`. Preserve the fetch, persist, and deduplication pipeline for BBVA, Eurocaja Rural, PayPal, and CSV imports.
- Financial analytics must exclude transactions where `excluir_de_gastos` is true. Internal transfers use `transfer_pair_id` and `transfer_estado`; PayPal passthrough bank charges must not be counted twice.
- Use `Decimal` for monetary business logic and preserve rounding at API boundaries. Handle external input errors at the HTTP or adapter boundary with specific, meaningful responses.
- Keep startup seeding idempotent. Alembic is authoritative for schema changes; `Base.metadata.create_all()` does not replace migrations.
- Focused validation: `python -m compileall -q app`, `alembic check`, `alembic heads`, `alembic current`, and `alembic upgrade head` as appropriate. With services running, check `/openapi.json` and the affected `/api/v1` endpoint.
- Read [CLAUDE.md](../../CLAUDE.md) for sync and domain rules and [backend/.env.example](../../backend/.env.example) for local and Docker configuration.