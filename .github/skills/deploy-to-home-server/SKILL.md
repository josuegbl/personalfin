---
name: deploy-to-home-server
description: 'Deploy BankFinances code to the home server at josue@192.168.1.51 via SSH: rsync local changes, then rebuild and restart Docker Compose services. Use when the user asks to "deploy", "push to the server", "deploy to production", "sync to 192.168.1.51", or "update the running app".'
argument-hint: 'Optional: specific service to deploy (backend, frontend, or omit for both)'
---

# Deploy to Home Server

Deploys the current local state of BankFinances to the home server at `josue@192.168.1.51` (key-based SSH, no password needed) and restarts it via Docker Compose.

Remote project path: `/home/josue/BankFinances`

## When to Use
- User asks to deploy, ship, or push current changes to the home server.
- User asks to sync/update the running instance at 192.168.1.51.

## Procedure

1. **Confirm clean state locally.** Run `git status` in the repo root; if there are uncommitted changes the user cares about, confirm with them whether to deploy as-is (rsync copies the working tree, not just committed code).

2. **Verify SSH connectivity** before doing anything destructive:
   ```bash
   ssh josue@192.168.1.51 'echo ok'
   ```
   If this fails or prompts for a password, stop and tell the user — do not attempt to work around SSH auth issues silently.

3. **Rsync the project**, excluding local-only and generated directories:
   ```bash
   rsync -avz --delete \
     --exclude '.git' \
     --exclude '.env' \
     --exclude 'backend/.venv' \
     --exclude 'backend/__pycache__' \
     --exclude 'frontend/node_modules' \
     --exclude 'frontend/dist' \
     ./ josue@192.168.1.51:/home/josue/BankFinances/
   ```
   - `--exclude '.env'` protects remote-only secrets/config from being overwritten by a missing or different local `.env`. If the user explicitly wants `.env` synced too, ask first.
   - Adjust the exclude list if the repo's `.gitignore` has more entries worth excluding.

4. **Rebuild and restart the affected services** on the remote host:
   ```bash
   ssh josue@192.168.1.51 'cd /home/josue/BankFinances && docker compose up -d --build <service...>'
   ```
   - Omit `<service...>` to rebuild/restart everything (`db`, `backend`, `frontend`).
   - If the user only changed backend or frontend code, restrict to that service to avoid unnecessary downtime elsewhere, e.g. `docker compose up -d --build backend`.

5. **Verify the deployment**:
   ```bash
   ssh josue@192.168.1.51 'cd /home/josue/BankFinances && docker compose ps'
   ssh josue@192.168.1.51 'cd /home/josue/BankFinances && docker compose logs --tail=50 backend'
   ```
   Confirm containers are `Up`/healthy and there are no startup errors in the logs.

6. **Report back** to the user: what was synced, which services were rebuilt, and the final container status. Flag any errors from the logs instead of assuming success.

## Notes
- Never force-overwrite `.env` or other secret files on the remote without explicit confirmation.
- This mechanism does not run Alembic migrations automatically — if the deploy includes schema changes, tell the user to run `alembic upgrade head` on the remote (inside the backend container or via `docker compose exec backend alembic upgrade head`) and confirm before doing so, since migrations are not easily reversible.
- If `rsync` or `ssh` commands are not available or fail unexpectedly, stop and report — do not fall back to `scp` or manual file copying without checking with the user first.
