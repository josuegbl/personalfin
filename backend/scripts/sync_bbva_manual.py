"""
Sync semi-automático de BBVA.

El usuario inicia sesión manualmente en la ventana que abre Playwright.
Una vez dentro de web.bbva.es el script toma el control: navega a la cuenta
indicada, descarga el Excel de movimientos y lo envía al backend.

Uso:
    cd backend
    .venv/bin/python3 scripts/sync_bbva_manual.py [ACCOUNT_ID]

Variables de entorno (opcionales):
    BACKEND_URL    URL base del backend  (default: http://localhost:8000)
    ACCOUNT_ID     ID de la cuenta BBVA  (puede pasarse como argumento)
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

sys.path.insert(0, str(Path(__file__).parent))
from _sync_utils import get_account, upload_file, resolve_account_id

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
LOGIN_URL   = "https://www.bbva.es/nimbus/signin.html"
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--start-maximized",
]


# ---------------------------------------------------------------------------
# Helpers de navegación
# ---------------------------------------------------------------------------

def _wait_spa(page: Page, timeout: int = 20_000) -> None:
    """Espera a que la SPA de web.bbva.es termine de renderizar."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(2_000)


def _click_account_by_iban(page: Page, iban: str) -> None:
    """
    Localiza la tarjeta de cuenta por IBAN y hace clic.

    Args:
        page: Página de Playwright (ya en web.bbva.es).
        iban: IBAN normalizado (sin espacios, mayúsculas).

    Raises:
        RuntimeError: Si no se encuentra la tarjeta con ese IBAN.
    """
    suffix = iban[-4:]
    for text in (iban, suffix):
        for sel in (
            f"[class*='product-list']:has-text('{text}')",
            f"[class*='product']:has-text('{text}')",
            f"[class*='account']:has-text('{text}')",
            f"article:has-text('{text}')",
            f"li:has-text('{text}')",
            f"[class*='card']:has-text('{text}')",
        ):
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2_000):
                    el.click()
                    _wait_spa(page, timeout=8_000)
                    print(f"  Cuenta encontrada con selector: {sel!r}")
                    return
            except Exception:
                pass

    page.screenshot(path="/tmp/bbva_dashboard.png")
    print("  📸 Screenshot del dashboard: /tmp/bbva_dashboard.png")
    raise RuntimeError(
        f"No se encontró la tarjeta de cuenta con IBAN {iban!r} (últimos 4: {suffix}). "
        "Asegúrate de que el IBAN en la base de datos coincide con el del portal."
    )


def _download_movements_excel(page: Page) -> bytes:
    """
    Desde la página de detalle de cuenta, navega a movimientos y descarga el Excel.

    Returns:
        Contenido del archivo .xlsx.

    Raises:
        RuntimeError: Si no se encuentra el botón de descarga.
    """
    page.screenshot(path="/tmp/bbva_account_page.png")
    print(f"  URL actual: {page.url}")
    print("  📸 Screenshot de la cuenta: /tmp/bbva_account_page.png")

    # Pestaña movimientos
    moved_to_movements = False
    for sel in (
        "[role='tab']:has-text('Movimientos')",
        "a:has-text('Movimientos')",
        "button:has-text('Movimientos')",
        "li:has-text('Movimientos')",
        "span:has-text('Movimientos')",
        "[aria-label*='movimientos']",
        "[aria-label*='Movimientos']",
        "[class*='tab']:has-text('Movimientos')",
    ):
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                _wait_spa(page, timeout=10_000)
                print(f"  Pestaña movimientos con: {sel!r}")
                moved_to_movements = True
                break
        except Exception:
            pass

    if not moved_to_movements:
        tabs = page.evaluate("""
            Array.from(document.querySelectorAll('[role=tab], [class*=tab] a, [class*=tab] button'))
                .map(e => e.innerText.trim()).filter(t => t)
        """)
        print(f"  Pestañas encontradas: {tabs}")

    page.screenshot(path="/tmp/bbva_movements_page.png")
    print("  📸 Screenshot movimientos: /tmp/bbva_movements_page.png")

    # Botón de descarga
    for sel in (
        "[class*='c-icon-download']",
        "button[aria-label*='descargar']",
        "button[aria-label*='Descargar']",
        "button[aria-label*='Excel']",
        "button:has-text('Descargar')",
        "button:has-text('Excel')",
        "a[download]",
        "button:has(i[class*='download'])",
        "button:has([class*='c-icon-download'])",
        "[title*='Excel']",
        "[title*='descargar']",
    ):
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"  Descargando con: {sel!r}")
                with page.expect_download(timeout=30_000) as dl_info:
                    el.click()
                dl = dl_info.value
                tmp = tempfile.mktemp(suffix=".xlsx")
                dl.save_as(tmp)
                try:
                    return Path(tmp).read_bytes()
                finally:
                    os.unlink(tmp)
        except Exception:
            pass

    buttons = page.evaluate("""
        Array.from(document.querySelectorAll('button, a[href]'))
            .filter(e => e.offsetParent !== null)
            .map(e => ({text: e.innerText.trim().slice(0,40), cls: e.className.slice(0,60), aria: e.getAttribute('aria-label') || ''}))
            .filter(e => e.text || e.aria)
            .slice(0, 20)
    """)
    print("  Botones visibles en la página:")
    for b in buttons:
        print(f"    {b}")

    raise RuntimeError(
        "No se encontró el botón de descarga en la página de movimientos. "
        "Revisa /tmp/bbva_movements_page.png para ver el estado de la página."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Punto de entrada del script de sync manual de BBVA."""
    account_id = resolve_account_id(BACKEND_URL, "BBVA", sys.argv[1:])
    account    = get_account(BACKEND_URL, account_id)
    iban       = (account.get("iban") or "").replace(" ", "").upper()
    alias      = account.get("alias", f"cuenta {account_id}")

    print(f"\nSincronizando: {alias} (ID: {account_id})")
    if iban:
        print(f"IBAN: {iban}")
    else:
        print("⚠ Sin IBAN registrado — deberás navegar manualmente a la cuenta.")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=False, slow_mo=300, args=BROWSER_ARGS)
            print("Usando Google Chrome del sistema")
        except Exception:
            browser = p.chromium.launch(headless=False, slow_mo=300, args=BROWSER_ARGS)
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
        page = ctx.new_page()

        # ── Paso 1: Login manual ────────────────────────────────────────────
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
        print("\n" + "="*60)
        print("  INICIA SESIÓN EN LA VENTANA DEL NAVEGADOR")
        print("  El script continuará automáticamente tras el login.")
        print("  Tienes 3 minutos.")
        print("="*60 + "\n")

        try:
            page.wait_for_url("**/web.bbva.es/**", timeout=180_000)
        except Exception:
            print("❌ Tiempo agotado esperando el login. Saliendo.")
            browser.close()
            sys.exit(1)

        print(f"✅ Login detectado. URL: {page.url}")
        _wait_spa(page, timeout=25_000)

        # ── Paso 2: Navegar a la cuenta ─────────────────────────────────────
        if iban:
            print(f"\nNavegando a la cuenta ({iban[-4:]})...")
            try:
                _click_account_by_iban(page, iban)
            except RuntimeError as e:
                print(f"⚠ {e}")
                print("Navega manualmente a la cuenta y pulsa Enter para continuar...")
                input()
        else:
            print("Navega manualmente a la cuenta y pulsa Enter cuando estés en la página de detalle...")
            input()

        # ── Paso 3: Descargar Excel ─────────────────────────────────────────
        print("Descargando Excel de movimientos...")
        try:
            xlsx_bytes = _download_movements_excel(page)
            print(f"✅ Excel descargado ({len(xlsx_bytes):,} bytes)")
        except RuntimeError as e:
            print(f"❌ Error descargando: {e}")
            browser.close()
            sys.exit(1)

        browser.close()

    # ── Paso 4: Enviar al backend ───────────────────────────────────────────
    print(f"\nEnviando al backend ({BACKEND_URL})...")
    try:
        result = upload_file(
            BACKEND_URL, account_id,
            "movimientos_bbva.xlsx", xlsx_bytes,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"\n✅ Importación completada:")
    print(f"   Nuevas transacciones: {result.get('imported', 0)}")
    print(f"   Total en archivo:     {result.get('total_in_file', 0)}")
    print(f"   Movimientos ya existentes omitidos:  {result.get('skipped_existing', 0)}")
    if result.get("balance"):
        print(f"   Saldo actualizado:    {result['balance']:.2f} €")


if __name__ == "__main__":
    main()
