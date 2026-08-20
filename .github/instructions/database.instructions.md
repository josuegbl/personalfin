---
name: "BankFinances Database"
description: "Use when changing PostgreSQL schema, Alembic migrations, SQLAlchemy models, database sessions, constraints, enums, arrays, indexes, or data backfills."
applyTo: ["backend/alembic/**/*.py", "backend/app/models/**/*.py", "backend/app/core/database.py", "backend/app/core/config.py"]
---

# Database Instructions

- The database is PostgreSQL 16. Do not assume SQLite compatibility: migrations use native enums, PostgreSQL arrays, numeric columns, and self-referencing foreign keys.
- Register every new SQLAlchemy model in `backend/app/models/__init__.py` so Alembic autogenerate can discover it. Keep model changes, Pydantic schemas, routers, and migrations aligned.
- Create migrations from `backend/` with `alembic revision --autogenerate -m "description"`, then review the generated file manually. Check enum creation/removal, PostgreSQL `ARRAY(Integer)`, server defaults, nullable changes, indexes, constraints, data backfills, and destructive operations.
- Preserve the linear migration history and make data transformations explicit and reversible where practical. Do not rely on `Base.metadata.create_all()` to apply migration behavior.
- Preserve financial invariants: transaction hashes support application-level deduplication; `excluir_de_gastos=true` excludes spending; complete internal transfers are linked by `transfer_pair_id`; monetary values use `NUMERIC` and Python `Decimal`.
- Preserve compatibility fields in forecast and recurring-income tables, including legacy income columns and the `guardado`/per-person planned-income path. Treat `meses=None` as the catch-all recurring-expense tier.
- Validate before and after migration changes from `backend/`: `alembic check`, `alembic heads`, `alembic current`, and `alembic upgrade head`. Review the diff and inspect the resulting schema against the model.
- Run `docker compose config --quiet` when changing database service configuration. Use `DATABASE_URL` with host `db` in Docker and `localhost` for local development.
- Read [CLAUDE.md](../../CLAUDE.md) for the data model and deduplication rules, and [Plan_Desarrollo_Economia_Familiar.md](../../Plan_Desarrollo_Economia_Familiar.md) for financial semantics.