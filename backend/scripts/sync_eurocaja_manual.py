"""
Sync semi-automático de Eurocaja Rural.

El portal de Eurocaja (ruralvia.com) abre en una nueva pestaña al pulsar
"ACCESO CLIENTES". Playwright intercepta todas las pestañas del contexto para
capturar la descarga del CSV dondequiera que ocurra.

Flujo:
  1. Se abre Chrome en https://www.eurocajarural.es/banca-online/
  2. El usuario pulsa "ACCESO CLIENTES", inicia sesión y navega a movimientos
  3. El usuario descarga el CSV desde el portal
  4. El script detecta la descarga automáticamente y la envía al backend

Uso:
    cd backend
    .venv/bin/python3 scripts/sync_eurocaja_manual.py [ACCOUNT_ID]

Variables de entorno (opcionales):
    BACKEND_URL    URL base del backend  (default: http://localhost:8000)
    ACCOUNT_ID     ID de la cuenta de Eurocaja Rural
"""

import os
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright, BrowserContext, Page

sys.path.insert(0, str(Path(__file__).parent))
from _sync_utils import get_account, upload_file, resolve_account_id

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BACKEND_URL  = os.environ.get("BACKEND_URL", "http://localhost:8000")
START_URL    = "https://www.eurocajarural.es/banca-online/"
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--start-maximized",
]
# Tiempo máximo que el usuario tiene para descargar el CSV (10 minutos)
DOWNLOAD_TIMEOUT_MS = 600_000


# ---------------------------------------------------------------------------
# Lógica de descarga
# ---------------------------------------------------------------------------

def _register_download_listener(page: Page, download_event: threading.Event, result: dict) -> None:
    """
    Registra un listener de descargas en la página dada.
    Cuando se detecte una descarga de CSV, guarda el contenido en result['bytes']
    y activa download_event.

    Args:
        page: Página de Playwright donde registrar el listener.
        download_event: Evento para señalizar al hilo principal.
        result: Diccionario compartido donde guardar los bytes descargados.
    """
    def on_download(download):
        if result.get("bytes"):
            return
        suggested = download.suggested_filename.lower()
        if not (suggested.endswith(".csv") or suggested.endswith(".xls") or suggested.endswith(".xlsx")):
            print(f"  Ignorando descarga no relevante: {download.suggested_filename}")
            return
        print(f"\n  📥 Descarga detectada: {download.suggested_filename}")
        tmp = tempfile.mktemp(suffix=Path(download.suggested_filename).suffix)
        download.save_as(tmp)
        result["bytes"]    = Path(tmp).read_bytes()
        result["filename"] = download.suggested_filename
        os.unlink(tmp)
        download_event.set()

    page.on("download", on_download)


def _register_on_new_page(ctx: BrowserContext, download_event: threading.Event, result: dict) -> None:
    """
    Escucha nuevas pestañas abiertas en el contexto y registra el listener
    de descargas en cada una.

    Args:
        ctx: Contexto del navegador.
        download_event: Evento para señalizar al hilo principal.
        result: Diccionario compartido donde guardar los bytes descargados.
    """
    def on_page(page: Page):
        print(f"  Nueva pestaña: {page.url or '(cargando...)'}")
        _register_download_listener(page, download_event, result)

    ctx.on("page", on_page)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Punto de entrada del script de sync manual de Eurocaja Rural."""
    account_id = resolve_account_id(BACKEND_URL, "Eurocaja Rural", sys.argv[1:])
    account    = get_account(BACKEND_URL, account_id)
    alias      = account.get("alias", f"cuenta {account_id}")

    print(f"\nSincronizando: {alias} (ID: {account_id})")

    download_event = threading.Event()
    result: dict   = {}

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=200, args=BROWSER_ARGS)
            print("Usando Google Chrome del sistema")
        except Exception:
            browser = p.chromium.launch(headless=False, slow_mo=200, args=BROWSER_ARGS)
            print("Usando Chromium de Playwright")

        ctx = browser.new_context(
            locale="es-ES",
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Escuchar nuevas pestañas antes de crear la primera página
        _register_on_new_page(ctx, download_event, result)

        page = ctx.new_page()
        _register_download_listener(page, download_event, result)

        page.goto(START_URL, wait_until="domcontentloaded", timeout=30_000)

        print("\n" + "="*60)
        print("  INSTRUCCIONES:")
        print("  1. Pulsa 'ACCESO CLIENTES' para entrar al portal")
        print("  2. Inicia sesión con tus credenciales")
        print("  3. Navega a tu cuenta y descarga el extracto CSV")
        print("  El script enviará el archivo al backend automáticamente.")
        print(f"  Tienes {DOWNLOAD_TIMEOUT_MS // 60_000} minutos.")
        print("="*60 + "\n")

        # Esperar a que el usuario descargue el archivo
        detected = download_event.wait(timeout=DOWNLOAD_TIMEOUT_MS / 1_000)

        browser.close()

    if not detected or not result.get("bytes"):
        print("❌ Tiempo agotado sin detectar descarga. Saliendo.")
        sys.exit(1)

    print(f"✅ Archivo capturado: {result['filename']} ({len(result['bytes']):,} bytes)")

    # ── Enviar al backend ───────────────────────────────────────────────────
    print(f"\nEnviando al backend ({BACKEND_URL})...")
    filename = result["filename"]
    mime = "text/csv" if filename.lower().endswith(".csv") else "application/octet-stream"
    try:
        upload_result = upload_file(BACKEND_URL, account_id, filename, result["bytes"], mime)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"\n✅ Importación completada:")
    print(f"   Nuevas transacciones: {upload_result.get('imported', 0)}")
    print(f"   Total en archivo:     {upload_result.get('total_in_file', 0)}")
    print(f"   Movimientos ya existentes omitidos:  {upload_result.get('skipped_existing', 0)}")
    if upload_result.get("balance"):
        print(f"   Saldo actualizado:    {upload_result['balance']:.2f} €")


if __name__ == "__main__":
    main()
