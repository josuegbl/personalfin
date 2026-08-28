"""
Inspección BBVA — tercera pasada: login completo + exploración post-login.

Objetivos:
  1. Confirmar que el login funciona con credenciales reales.
  2. Detectar si BBVA pide 2FA (OTP por SMS u otro).
  3. Navegar hasta la sección de movimientos de cada cuenta.
  4. Localizar y probar el botón de descarga/exportación de extracto.
  5. Interceptar la request de descarga para capturar la URL/payload exactos.

Resultados esperados:
  - Screenshots en /tmp/bbva3_inspect/
  - HTML de cada pantalla clave en /tmp/bbva3_inspect/*.html
  - Log en consola con URLs, selectores y cualquier request de descarga

Uso:
    cd backend
    pip install playwright && playwright install chromium
    python3 scripts/inspect_bbva3.py

Requiere en backend/.env:
    BBVA_CUENTA_A_USER=<tu_NIF>
    BBVA_CUENTA_A_PASSWORD=<tu_clave_de_acceso>
"""

import os
import sys
import json
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from playwright.sync_api import sync_playwright, Page, BrowserContext

OUT_DIR = Path("/tmp/bbva3_inspect")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BBVA_USER = os.environ.get("BBVA_CUENTA_A_USER", "")
BBVA_PASS = os.environ.get("BBVA_CUENTA_A_PASSWORD", "")
LOGIN_URL  = "https://www.bbva.es/nimbus/signin.html"

if not BBVA_USER or not BBVA_PASS:
    print("ERROR: Define BBVA_CUENTA_A_USER y BBVA_CUENTA_A_PASSWORD en backend/.env")
    sys.exit(1)

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--start-maximized",
]

# Requests de descarga que queremos interceptar
DOWNLOAD_KEYWORDS = ("csv", "excel", "xls", "xlsx", "export", "download", "descarga", "extracto")

intercepted_requests: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def shot(page: Page, name: str):
    path = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  📸 {path}")


def save_html(page: Page, name: str):
    path = OUT_DIR / f"{name}.html"
    path.write_text(page.content(), encoding="utf-8")
    print(f"  💾 HTML: {path}")


def dump_elements(page: Page, label: str, selector: str = "input, button, a[href], select"):
    print(f"\n--- {label} ---")
    print(f"  URL: {page.url}")
    els = page.query_selector_all(selector)
    for el in els[:40]:
        try:
            tag   = el.evaluate("e => e.tagName.toLowerCase()")
            t     = el.get_attribute("type") or ""
            name  = el.get_attribute("name") or ""
            id_   = el.get_attribute("id") or ""
            ph    = el.get_attribute("placeholder") or ""
            href  = el.get_attribute("href") or ""
            cls   = (el.get_attribute("class") or "")[:80]
            txt   = (el.inner_text() or "")[:50].replace("\n", " ").strip()
            vis   = el.is_visible()
            print(
                f"  <{tag} type={t!r} name={name!r} id={id_!r} "
                f"placeholder={ph!r} href={href[:60]!r} text={txt!r} "
                f"visible={vis} class={cls!r}>"
            )
        except Exception:
            pass


def on_request(request):
    url = request.url.lower()
    if any(kw in url for kw in DOWNLOAD_KEYWORDS):
        entry = {
            "method": request.method,
            "url": request.url,
            "headers": dict(request.headers),
            "post_data": request.post_data,
        }
        intercepted_requests.append(entry)
        print(f"\n  ⬇ Request de descarga interceptada:")
        print(f"    {request.method} {request.url}")


# ---------------------------------------------------------------------------
# Flujo principal
# ---------------------------------------------------------------------------

def step_login(page: Page) -> bool:
    """Realiza el login. Devuelve True si parece que tuvo éxito."""
    print("\n[1] Navegando a la página de login…")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(2_000)
    shot(page, "01_login_page")

    print("\n[2] Rellenando usuario…")
    for sel in [
        "input[placeholder='Usuario']",
        "input[type='text']",
        "input[autocomplete='username']",
        "input[name*='user']",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.fill(sel, BBVA_USER)
                print(f"  ✓ Usuario con: {sel}")
                break
        except Exception:
            pass

    print("\n[3] Rellenando contraseña…")
    for sel in [
        "input[placeholder='Clave de acceso']",
        "input[type='password']",
        "input[autocomplete='current-password']",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.fill(sel, BBVA_PASS)
                print(f"  ✓ Contraseña con: {sel}")
                break
        except Exception:
            pass

    shot(page, "02_credentials_filled")

    print("\n[4] Submit…")
    for sel in [
        "button:has-text('Iniciar sesión')",
        "button[type='submit']",
        "input[type='submit']",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.click(sel)
                print(f"  ✓ Submit con: {sel}")
                break
        except Exception:
            pass

    print("  Esperando respuesta post-login (15 s)…")
    page.wait_for_timeout(15_000)
    shot(page, "03_post_login")
    save_html(page, "03_post_login")
    print(f"  URL post-login: {page.url}")
    dump_elements(page, "Post-login")

    # Heurística: si seguimos en nimbus/signin, el login falló
    if "signin" in page.url or "login" in page.url.lower():
        print("\n  ⚠ Parece que el login falló (seguimos en la página de login).")
        return False

    return True


def step_detect_2fa(page: Page) -> bool:
    """Detecta si BBVA pide un segundo factor. Devuelve True si lo detecta."""
    otp_clues = [
        "input[placeholder*='código']",
        "input[placeholder*='OTP']",
        "input[placeholder*='SMS']",
        "*:has-text('código de seguridad')",
        "*:has-text('verificación')",
        "*:has-text('segundo factor')",
        "*:has-text('Coordenadas')",
    ]
    for sel in otp_clues:
        try:
            if page.query_selector(sel):
                print(f"\n  🔐 2FA detectado con selector: {sel}")
                shot(page, "04_2fa_prompt")
                save_html(page, "04_2fa_prompt")
                return True
        except Exception:
            pass
    print("\n  ✓ No se detectó prompt de 2FA.")
    return False


def step_explore_accounts(page: Page):
    """Navega a la sección de cuentas y lista las disponibles."""
    print("\n[5] Explorando sección de cuentas…")

    # Intentar navegar directamente si el botón no es obvio
    candidate_urls = [
        "https://www.bbva.es/general/banca-online/banca-online.html",
        "https://www.bbva.es/particulares/mis-cuentas.html",
    ]
    current = page.url
    if not any(u in current for u in ["banca-online", "mis-cuentas", "cuentas"]):
        for url in candidate_urls:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                page.wait_for_timeout(3_000)
                print(f"  Cargado: {page.url}")
                shot(page, "05_cuentas_home")
                break
            except Exception as e:
                print(f"  Fallo {url}: {e}")

    # Buscar tarjetas/links de cuentas corrientes
    print("\n  Links de cuentas encontrados:")
    links = page.query_selector_all("a, button, [role='button']")
    account_links = []
    for link in links:
        try:
            txt  = (link.inner_text() or "").strip().lower()
            href = (link.get_attribute("href") or "").lower()
            cls  = (link.get_attribute("class") or "").lower()
            if any(kw in txt or kw in href or kw in cls
                   for kw in ["cuenta", "saldo", "corriente", "ahorro"]):
                if link.is_visible():
                    print(f"    text={txt[:60]!r} href={href[:80]!r}")
                    account_links.append(link)
        except Exception:
            pass

    return account_links


def step_explore_movements(page: Page, account_links: list):
    """Entra en la primera cuenta e intenta llegar a movimientos."""
    print("\n[6] Entrando en la primera cuenta para ver movimientos…")

    if account_links:
        try:
            account_links[0].click()
            page.wait_for_timeout(4_000)
        except Exception as e:
            print(f"  Click en cuenta falló: {e}")

    shot(page, "06_account_detail")
    save_html(page, "06_account_detail")
    dump_elements(page, "Detalle de cuenta")

    # Buscar pestaña/botón de movimientos
    print("\n  Buscando sección de movimientos…")
    for sel in [
        "a:has-text('Movimientos')",
        "button:has-text('Movimientos')",
        "a:has-text('movimientos')",
        "[aria-label*='movimientos']",
        "a[href*='movimiento']",
        "a:has-text('Extracto')",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"  ✓ Movimientos con: {sel}")
                el.click()
                page.wait_for_timeout(3_000)
                shot(page, "07_movements")
                save_html(page, "07_movements")
                dump_elements(page, "Pantalla de movimientos")
                break
        except Exception:
            pass


def step_find_download(page: Page):
    """Busca el botón de descarga/exportación de movimientos."""
    print("\n[7] Buscando botón de descarga/exportación…")
    shot(page, "08_before_download_search")

    download_selectors = [
        # Iconos/botones de descarga habituales en BBVA
        "button[aria-label*='descargar']",
        "button[aria-label*='exportar']",
        "button[title*='descargar']",
        "button[title*='exportar']",
        "button[title*='CSV']",
        "button[title*='Excel']",
        "a[href*='csv']",
        "a[href*='excel']",
        "a[href*='xls']",
        "a[download]",
        # Iconos SVG dentro de botones (BBVA usa mucho esto)
        "button:has([class*='download'])",
        "button:has([class*='export'])",
        "[class*='download-btn']",
        "[class*='export-btn']",
        # Textos explícitos
        "button:has-text('Descargar')",
        "button:has-text('Exportar')",
        "button:has-text('CSV')",
        "button:has-text('Excel')",
        "a:has-text('Descargar extracto')",
        "a:has-text('Exportar movimientos')",
    ]

    found_any = False
    for sel in download_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                txt = (el.inner_text() or "")[:60].strip()
                cls = (el.get_attribute("class") or "")[:80]
                print(f"  ✓ Candidato de descarga: selector={sel!r} tag={tag} text={txt!r} class={cls!r}")
                found_any = True
        except Exception:
            pass

    if not found_any:
        print("  ✗ No se encontró botón de descarga obvio.")
        print("    Volcando todos los botones/links de la página para análisis manual…")
        dump_elements(page, "Todos los elementos — búsqueda manual de descarga",
                      "button, a[href], [role='button'], [class*='icon']")

    # Intentar abrir un selector de formato si hay menú de descarga
    _try_click_download(page)


def _try_click_download(page: Page):
    """Intenta hacer clic en el botón de descarga y registra lo que ocurre."""
    print("\n  Intentando clic en el primer candidato de descarga encontrado…")
    for sel in [
        "button:has-text('Descargar')",
        "button[title*='descargar']",
        "button[aria-label*='descargar']",
        "a[href*='csv']",
        "a[download]",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                # Interceptar posible diálogo de descarga
                with page.expect_download(timeout=8_000) as dl_info:
                    el.click()
                try:
                    dl = dl_info.value
                    dest = OUT_DIR / f"descarga_{dl.suggested_filename}"
                    dl.save_as(str(dest))
                    print(f"  ✅ Archivo descargado: {dest}")
                except Exception:
                    pass
                page.wait_for_timeout(3_000)
                shot(page, "09_after_download_click")
                save_html(page, "09_after_download_click")
                dump_elements(page, "Tras clic de descarga")
                break
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                slow_mo=300,
                args=STEALTH_ARGS,
            )
            print("✓ Usando Google Chrome del sistema")
        except Exception:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=300,
                args=STEALTH_ARGS,
            )
            print("⚠ Chrome no disponible, usando Chromium con stealth args")

        ctx: BrowserContext = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
            accept_downloads=True,
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = ctx.new_page()
        page.on("request", on_request)

        # ── Flujo ──────────────────────────────────────────────────────────
        logged_in = step_login(page)

        if not logged_in:
            print("\n❌ No se pudo completar el login. Comprueba las credenciales.")
            print(f"   Screenshots en: {OUT_DIR}")
            print("   Navegador abierto 30 s para inspección manual…")
            page.wait_for_timeout(30_000)
            browser.close()
            return

        has_2fa = step_detect_2fa(page)

        if has_2fa:
            print("\n🔐 BBVA pidió un segundo factor.")
            print("   El sync automático desatendido NO es viable con 2FA activo.")
            print("   Opciones:")
            print("     A) Usar la app BBVA para pre-autorizar la sesión (cookie persistente).")
            print("     B) Mantener el modelo de importación CSV manual.")
            print("   Screenshots en:", OUT_DIR)
            print("   Navegador abierto 60 s para que puedas completar el 2FA manualmente…")
            page.wait_for_timeout(60_000)
            # Re-intentar exploración tras 2FA manual
            shot(page, "04b_after_manual_2fa")

        account_links = step_explore_accounts(page)
        step_explore_movements(page, account_links)
        step_find_download(page)

        # Resumen de requests de descarga interceptadas
        if intercepted_requests:
            print("\n📋 Requests de descarga capturadas:")
            report_path = OUT_DIR / "download_requests.json"
            report_path.write_text(
                json.dumps(intercepted_requests, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            for r in intercepted_requests:
                print(f"  {r['method']} {r['url']}")
            print(f"  Guardadas en: {report_path}")
        else:
            print("\n  No se interceptaron requests de descarga.")

        print(f"\n✅ Inspección completada. Revisa screenshots en: {OUT_DIR}")
        print("   Navegador abierto 30 s para inspección manual…")
        page.wait_for_timeout(30_000)
        browser.close()


if __name__ == "__main__":
    main()
