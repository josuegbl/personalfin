# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BankFinances is a private family finance management app. It syncs bank accounts (BBVA, Eurocaja Rural) and PayPal, then provides a dashboard with spending analysis, recurring expense tracking, and monthly forecasting.

## Development Commands

### Full stack (Docker)

```bash
# Start all services (db + backend + frontend)
docker compose up -d

# Rebuild after dependency changes
docker compose up -d --build

# View backend logs
docker compose logs -f backend
```

### Backend (local dev, outside Docker)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run dev server (requires DB on localhost:5432)
uvicorn app.main:app --reload

# Apply migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"
```

### Frontend (local dev, outside Docker)

```bash
cd frontend
npm install
npm run dev      # Vite dev server on :5173
npm run build    # TypeScript check + production build
```

### Sync manual de BBVA

BBVA bloquea los browsers headless. El flujo es semi-automático: Playwright abre
el navegador visible, el usuario inicia sesión, y el script descarga el Excel y lo
envía al backend.

```bash
cd backend

# Sincronizar la cuenta BBVA con ID 1
BACKEND_URL=http://localhost:8000 .venv/bin/python3 scripts/sync_bbva_manual.py 1

# Si hay una sola cuenta BBVA, auto-detecta
BACKEND_URL=http://localhost:8000 .venv/bin/python3 scripts/sync_bbva_manual.py
```

### Diagnostic scripts

```bash
# Inspect CSV exports from banks (for adapter development)
cd backend
python scripts/inspect_bbva.py
python scripts/inspect_eurocaja.py
```

## Architecture

```
**Backend layout** (`backend/app/`):
- `api/v1/` — FastAPI routers: `accounts`, `transactions`, `categories`, `dashboard`, `sync`
- `models/` — SQLAlchemy ORM models (`Account`, `Transaction`, `Category`, `RecurringExpense`)
- `schemas/` — Pydantic request/response models
- `services/` — Business logic (no DB access in routers beyond dependency injection)
  - `sync/` — Bank and PayPal adapters (see below)
  - `categorization.py` — Rule-based transaction categorization
  - `recurring.py` — Recurring expense detection
- `core/` — `config.py` (Pydantic settings from `.env`), `database.py` (engine + session)
- `tasks/scheduler.py` — APScheduler daily sync at 07:00
- `seed.py` — Initial data for recurring/seasonal expenses

**Frontend layout** (`frontend/src/`):
- `pages/` — `Dashboard`, `Transactions`, `Categories`
- `api/client.ts` — Typed API client (single source of truth for all backend calls)
- `components/` — Shared UI components (`AccountCard`, `StatTile`)
- `hooks/` — React Query hooks
- `types/` — TypeScript interfaces mirroring backend schemas

## Sync Architecture

The `SourceAdapter` ABC (`services/sync/base.py`) defines the interface all adapters implement:
- `fetch_transactions() → list[RawTransaction]`
- `fetch_balance() → Decimal`
- `sync()` orchestrates fetch → persist, preserving the CSV/provider movement as the source of truth

**BBVA** has two sync modes:
- **Semi-automático** (recommended): `scripts/sync_bbva_manual.py` opens a browser, the user logs in, Playwright downloads the Excel and POSTs it to the backend. Requires headless=False; BBVA blocks all headless modes (PerimeterX/Kasada anti-bot).
- **Manual CSV upload**: `POST /api/v1/sync/{account_id}/upload` accepts both `.csv` and `.xlsx` (Excel downloaded manually from the BBVA portal). `BBVAAdapter.parse_csv_upload()` handles CSV; `parse_bbva_excel()` handles Excel.

`BBVAPlaywrightAdapter` is the automatic login adapter but it requires a display (Xvfb in Docker). The adapter selects its channel: `channel="chrome"` if Chrome is installed, otherwise Playwright Chromium.

**Eurocaja Rural** uses manual CSV upload only.

**PayPal** uses the REST API v2 (OAuth 2.0 client credentials) and supports automatic sync (`POST /api/v1/sync/{account_id}`).

`CSVImportAdapter` (in `base.py`) wraps already-parsed `RawTransaction` lists so they go through the same persist pipeline.

## Movement identity and categorization

The CSV/provider movement is the source of truth. Existing movements are skipped only when their SHA-256 `hash` matches `(account_id, fecha, importe, concepto)`; this prevents overlapping CSV imports from creating a second copy. This hash never changes financial meaning.

All imported and migrated movements start in `Sin categoría`. The user classifies them manually from the Movimientos screen. `Transferencias Internas` is a regular category and does not trigger account matching.

Basic dashboard and forecast totals use the sign of the movement: positive amounts are income and negative amounts are expenses, including `Sin categoría` and transfers. Category metadata is currently descriptive and supports breakdowns; category-specific inclusion rules will be defined later. Payroll movements retain the `Nómina` category.

## Data Model Key Points

- `categories.naturaleza` defines whether a category is a `gasto`, `ingreso`, `transferencia`, or `neutral`.
- `categories.incluida_en_analisis` controls whether categorized movements participate in dashboard and forecast totals.
- `accounts.proveedor` drives adapter selection: `"BBVA"`, `"Eurocaja Rural"`, `"PayPal"`.
- `accounts.sync_error` stores the last error message if a sync fails; `None` means OK.

## Startup Seeding

On every startup (`app.main.startup`), two idempotent seeds run if the tables are empty:
- **Categories** — hardcoded in `main.py` (`_seed_categories`)
- **Recurring/seasonal expenses** — loaded from `app/seed.py` (`RECURRING_EXPENSES`)

Alembic manages schema migrations; `Base.metadata.create_all` only fills gaps not covered by migrations.

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Required:
- `DATABASE_URL` — use the `db` hostname when running in Docker, `localhost` otherwise
- `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` — optional; PayPal can also be imported via CSV if not set

## API Base URL

All endpoints are prefixed `/api/v1`. Interactive docs available at `http://localhost:8000/docs`.
