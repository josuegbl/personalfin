# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BankFinances is a private family finance management app. It syncs bank accounts (BBVA, Eurocaja Rural) and PayPal, then provides a dashboard with spending analysis, recurring expense tracking, and monthly forecasting.

## Development Commands

### Backend (local dev)

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

### Frontend (local dev)

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

# Sincronizar la cuenta BBVA (auto-detecta si hay una sola)
BACKEND_URL=http://localhost:8000 .venv/bin/python3 scripts/sync_bbva_manual.py

# Con ID de cuenta explícito
BACKEND_URL=http://localhost:8000 .venv/bin/python3 scripts/sync_bbva_manual.py 1
```

### Sync manual de Eurocaja Rural

```bash
cd backend
BACKEND_URL=http://localhost:8000 .venv/bin/python3 scripts/sync_eurocaja_manual.py
```

### Diagnostic scripts

```bash
# Inspect CSV exports from banks (for adapter development)
cd backend
python scripts/inspect_bbva.py
python scripts/inspect_eurocaja.py
```

## Architecture

**Backend layout** (`backend/app/`):
- `api/v1/` — FastAPI routers: `accounts`, `transactions`, `categories`, `dashboard`, `sync`, `forecast`, `recurring_expenses`, `recurring_income`
- `models/` — SQLAlchemy ORM models: `Account`, `Transaction`, `Category`, `RecurringExpense`, `RecurringIncome`, `ForecastPlan`, `MonthlyBalancePlan`
- `schemas/` — Pydantic request/response models mirroring each router
- `services/` — Business logic (routers never access DB directly beyond dependency injection)
  - `sync/` — Bank and PayPal adapters (see Sync Architecture below)
  - `recurring.py` — Recurring expense detection
- `core/` — Infrastructure and configuration
  - `config.py` — Pydantic settings from `.env`
  - `database.py` — SQLAlchemy engine + session
  - `category_catalog.py` — Canonical category allowlist (single source of truth)
  - `forecast_catalog.py` — Fixed-category names for forecast grouping and aliases
  - `date_limits.py` — `MIN_ANIO`/`MIN_MES` constants; the app rejects forecast/dashboard requests before this date
- `tasks/scheduler.py` — APScheduler daily sync at 07:00
- `seed.py` — `RECURRING_EXPENSES` seed data; `ensure_forecast_catalog()` runs on startup

**Frontend layout** (`frontend/src/`):
- `pages/` — `Dashboard`, `Transactions`, `Categories`, `Forecast`
- `api/client.ts` — Typed API client (single source of truth for all backend calls)
- `components/` — `AccountCard`, `StatTile`, `UploadModal`
- `types/` — TypeScript interfaces mirroring backend schemas
- `utils/dateLimits.ts` — Minimum supported month constants (mirrors `date_limits.py`)
- `utils/format.ts` — Currency and date formatting helpers

## Sync Architecture

`SourceAdapter` ABC (`services/sync/base.py`) defines the interface all adapters implement:
- `fetch_transactions() → list[RawTransaction]`
- `fetch_balance() → Decimal`
- `sync()` orchestrates fetch → persist, preserving the CSV/provider movement as the source of truth

**BBVA** has two sync modes:
- **Semi-automático** (recommended): `scripts/sync_bbva_manual.py` opens a browser, the user logs in, Playwright downloads the Excel and POSTs it to the backend. Requires headless=False; BBVA blocks all headless modes (PerimeterX/Kasada anti-bot).
- **Manual CSV upload**: `POST /api/v1/sync/{account_id}/upload` accepts both `.csv` and `.xlsx`. `BBVAAdapter.parse_csv_upload()` handles CSV; `parse_bbva_excel()` handles Excel.

**Eurocaja Rural** uses manual CSV upload only (`scripts/sync_eurocaja_manual.py`).

**PayPal** uses the REST API v2 (OAuth 2.0 client credentials) and supports automatic sync (`POST /api/v1/sync/{account_id}`).

`CSVImportAdapter` (in `base.py`) wraps already-parsed `RawTransaction` lists so they go through the same persist pipeline.

## Movement identity and categorization

Existing movements are skipped when their SHA-256 `hash` matches `(account_id, fecha, importe, concepto)` — preventing duplicate CSV imports. This hash never changes financial meaning.

All imported movements start in `Sin categoría`. The user classifies them manually from the Movimientos screen. Payroll movements are auto-assigned the `Nómina` category via `_is_payroll()` in `base.py` (checks concepto/comercio for "NOMINA"/"NÓMINA" on positive amounts).

Dashboard and forecast totals use the sign of the movement: positive = income, negative = expense. `categories.incluida_en_analisis` controls whether a category participates in these totals.

## Forecast income model

Income in month M is split into two streams:
1. **Salary (nómina)** — positive transactions in category `Nómina` from month M-1 (prior month, because salaries arrive in one month and cover the next).
2. **Other income** — all other positive non-excluded transactions from month M itself.

`ahorro_real = ingresos_reales − total_gastos_reales − total_cuentas_personales`

Personal allocations (`cuenta_personal_josue/adi`) are deducted from savings but are not counted as "gastos" since they move to accounts outside the app.

## Balance closing

When a month ends, its `ForecastPlan` can be promoted to a `MonthlyBalancePlan` (frozen snapshot). Once a `MonthlyBalancePlan` exists for a month, `GET /api/v1/forecast/{year}/{month}` returns `_build_balance_response()` instead of the live plan — the planned values are locked. One-time corrections are possible via:
- `PUT /forecast/{year}/{month}/balance-snapshot` — corrects fixed/variable expense lines (locks `gastos_corregidos`)
- `PUT /forecast/{year}/{month}/income-correction` — corrects planned income (locks `ingresos_corregidos`)

Each correction endpoint is a one-shot: a second call returns 409.

## Category Governance

`backend/app/core/category_catalog.py` is the single source of truth for category names and parent relationships. Before changing application code or the database, review that list. Only categories in the canonical list may exist in the database; startup validation enforces this.

Categories are never created automatically by seeds or synchronization. `categories.naturaleza` is one of `gasto`, `ingreso`, `transferencia`, `neutral`.

`Category.codigo_sistema` is a stable identifier (`"nomina"`, `"sin_categoria"`) that survives renames. Use these codes — not the `nombre` field — to identify these special categories in business logic.

## Data Model Key Points

- `transactions.hash` — SHA-256 of `(account_id, fecha, importe, concepto)`. The deduplication key; never changes.
- `categories.naturaleza` — `gasto`, `ingreso`, `transferencia`, or `neutral`.
- `categories.incluida_en_analisis` — controls whether categorized movements participate in dashboard and forecast totals.
- `categories.codigo_sistema` — stable system identifier; use `CATEGORY_CODE_NOMINA` / `CATEGORY_CODE_SIN_CATEGORIA` constants.
- `accounts.proveedor` — drives adapter selection: `"BBVA"`, `"Eurocaja Rural"`, `"PayPal"`.
- `accounts.sync_error` — stores the last error message if a sync fails; `None` means OK.
- `recurring_expenses.tiers` — a recurring expense can have month-specific amounts (e.g. summer tariffs). `_tier_for_month()` selects the active tier; `meses=None` is the catch-all.
- `recurring_incomes.propietario` — `"josue"` or `"adi"` (case-insensitive match); used to split planned income in the forecast.
- `forecast_plans.guardado` — `True` once the user has explicitly saved a plan; ungarded plans inherit values from the most recent saved plan.
- `monthly_balance_plans` — frozen planned values for a closed month; takes precedence over `forecast_plans` for the same month.

## Startup Seeding

On every startup (`app.main.startup`), two idempotent seeds run:
- **Recurring expenses** — `RECURRING_EXPENSES` from `app/seed.py` (skipped if table is non-empty)
- **Forecast catalog** — `ensure_forecast_catalog()` from `app/seed.py`

`_validate_category_catalog()` also runs on startup and raises `RuntimeError` if any `SIGN_BASED_CATEGORY_NAMES` category has the wrong `naturaleza`.

Alembic manages schema migrations; `Base.metadata.create_all` only fills gaps not covered by migrations.

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Required:
- `DATABASE_URL` — PostgreSQL connection string (use `localhost:5432` for local dev)
- `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` — optional; PayPal can also be imported via CSV

## API Base URL

All endpoints are prefixed `/api/v1`. Interactive docs available at `http://localhost:8000/docs`.
