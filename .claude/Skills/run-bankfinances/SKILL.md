---
name: run-bankfinances
description: 'Run, start, launch, screenshot, or test the BankFinances app. Use when the user asks to "run the app", "open the dashboard", "test this change in the browser", or "take a screenshot".'
argument-hint: 'Optional: backend, frontend, or omit for both'
---

# Run BankFinances

BankFinances is a React + FastAPI web app. It runs on the home server at `192.168.1.51` via Docker Compose. The agent path is: start containers over SSH, hit the API with `curl`, and screenshot the frontend with Edge headless.

**Frontend:** `http://192.168.1.51:5173`  
**Backend API:** `http://192.168.1.51:8000/api/v1`  
**Remote project:** `/home/josue/BankFinances`

## Prerequisites

- SSH key access to `josue@192.168.1.51` (passwordless, already configured)
- Microsoft Edge installed at `/Applications/Microsoft Edge.app` (used for headless screenshots)

## Start the stack

```bash
ssh josue@192.168.1.51 'cd ~/BankFinances && docker compose up -d'
sleep 5
ssh josue@192.168.1.51 'docker compose -f ~/BankFinances/docker-compose.yml ps'
```

All three services (`db`, `backend`, `frontend`) must show `Up`. The `db` service has a healthcheck; wait for it before the backend is ready.

## Verify (agent path)

**API smoke test:**
```bash
curl -s http://192.168.1.51:8000/api/v1/accounts/ | python3 -m json.tool | head -20
```
Expect a JSON array of account objects with `alias`, `saldo_actual`, `proveedor`.

**Screenshot the dashboard:**
```bash
"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  --headless=new \
  --screenshot=/tmp/bankfinances-dashboard.png \
  --window-size=1400,900 \
  --no-sandbox \
  --disable-gpu \
  "http://192.168.1.51:5173" 2>/dev/null
```

Other routes: `/movimientos`, `/prevision`, `/categorias`. Replace the path at the end of the URL.

After taking the screenshot, **read it** with the Read tool to confirm the page rendered correctly (not blank, not an error).

## Run (human path)

If you need to start the stack and open a browser yourself:
```bash
ssh josue@192.168.1.51 'cd ~/BankFinances && docker compose up -d'
# then open http://192.168.1.51:5173 in a browser
```

## Stop the stack

```bash
ssh josue@192.168.1.51 'cd ~/BankFinances && docker compose down'
```

## Gotchas

- **Playwright MCP browser_navigate fails** — Chrome is not installed. Use the Edge headless `--screenshot` command above instead.
- **Backend startup error `column categories.codigo_sistema does not exist`** — the local database at `localhost:5432` is outdated (schema at migration 0005). Always use the server at `192.168.1.51`; never try to start the backend locally unless you recreate the local DB from scratch.
- **Migration 0017 fails on fresh local DB** — `DROP TYPE transactionorigin` fails because the column default still references the enum. Fixed in `alembic/versions/0017_remove_paypal_integration.py` (drop default before drop type).
- **`pg_isready -h 192.168.1.51 -p 5432`** will time out even when the DB is healthy — the port is not exposed externally; it's only accessible inside the Docker network.
- **`docker compose up -d --build`** takes ~30 s on a rebuild. If you only changed Python/TS source (no Dockerfile change), `--build` is still safe but slower; omit it if you just want to restart.
- **BBVA sync error on startup** — `sync_error` in the accounts response shows a Playwright error. This is expected; BBVA sync requires the semi-automatic desktop script, not the Docker container.
