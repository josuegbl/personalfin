"""
Inspección BBVA — cuarta pasada: exploración completa del portal web.bbva.es.

Lecciones de la tercera pasada:
  - El login redirige a https://web.bbva.es/index.html#posicion-global (SPA)
  - No hay que navegar a www.bbva.es — la sesión vive en web.bbva.es
  - BBVA carga excelmaker.js → hay exportación a Excel en el portal
  - Hay que esperar a que la SPA (React/Angular) termine de renderizar

Objetivos:
  1. Hacer login y quedarse en web.bbva.es
  2. Esperar a que carguen las tarjetas de cuentas
  3. Hacer clic en cada cuenta corriente
  4. Navegar a la sección de movimientos
  5. Encontrar y pulsar el botón de exportación (Excel / CSV)
  6. Interceptar la request de descarga y guardar el archivo

Uso:
    cd backend
    .venv/bin/python3 scripts/inspect_bbva4.py

Requiere en backend/.env: BBVA_JGB_USER y BBVA_JGB_PASSWORD
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from playwright.sync_api import sync_playwright, Page, BrowserContext

OUT_DIR = Path("/tmp/bbva4_inspect")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BBVA_USER = os.environ.get("BBVA_JGB_USER", "")
BBVA_PASS = os.environ.get("BBVA_JGB_PASSWORD", "")
LOGIN_URL  = "https://www.bbva.es/nimbus/signin.html"
PORTAL_URL = "https://web.bbva.es/"

if not BBVA_USER or not BBVA_PASS:
    print("ERROR: Define BBVA_JGB_USER y BBVA_JGB_PASSWORD en backend/.env")
    sys.exit(1)

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--start-maximized",
]

download_requests: list[dict] = []


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def shot(page: Page, name: str):
    path = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  📸 {path}")


def save_html(page: Page, name: str):
    path = OUT_DIR / f"{name}.html"
    path.write_text(page.content(), encoding="utf-8")
    print(f"  💾 HTML: {path}")


def dump_elements(page: Page, label: str, selector: str = "button, a[href]", limit: int = 40):
    print(f"\n--- {label} ---")
    print(f"  URL: {page.url}")
    for el in page.query_selector_all(selector)[:limit]:
        try:
            tag  = el.evaluate("e => e.tagName.toLowerCase()")
            t    = el.get_attribute("type") or ""
            id_  = el.get_attribute("id") or ""
            href = (el.get_attribute("href") or "")[:80]
            cls  = (el.get_attribute("class") or "")[:80]
            txt  = (el.inner_text() or "")[:60].replace("\n", " ").strip()
            aria = el.get_attribute("aria-label") or ""
            vis  = el.is_visible()
            print(
                f"  <{tag} type={t!r} id={id_!r} href={href!r} "
                f"aria-label={aria!r} text={txt!r} visible={vis} class={cls!r}>"
            )
        except Exception:
            pass


def wait_for_spa(page: Page, timeout: int = 20_000):
    """Espera a que la SPA de web.bbva.es termine de renderizar."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass
    page.wait_for_timeout(3_000)


# ---------------------------------------------------------------------------
# Paso 1: Login
# ---------------------------------------------------------------------------

def step_login(page: Page) -> bool:
    print("\n[1] Login en nimbus/signin.html…")
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(2_000)

    # Usuario
    for sel in ["input[placeholder='Usuario']", "input[type='text']"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.fill(sel, BBVA_USER)
                print(f"  ✓ Usuario: {sel}")
                break
        except Exception:
            pass

    # Contraseña
    for sel in ["input[placeholder='Clave de acceso']", "input[type='password']"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.fill(sel, BBVA_PASS)
                print(f"  ✓ Contraseña: {sel}")
                break
        except Exception:
            pass

    # Submit
    for sel in ["button:has-text('Iniciar sesión')", "button[type='submit']"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                page.click(sel)
                print(f"  ✓ Submit: {sel}")
                break
        except Exception:
            pass

    # Esperar hasta llegar a web.bbva.es
    print("  Esperando redirección a web.bbva.es (30 s máx)…")
    try:
        page.wait_for_url("**/web.bbva.es/**", timeout=30_000)
        print(f"  ✓ Redirigido a: {page.url}")
    except Exception:
        print(f"  ✗ No redirigió a web.bbva.es. URL actual: {page.url}")
        shot(page, "00_login_failed")
        return False

    # Dar tiempo extra al SPA para cargar
    wait_for_spa(page, timeout=25_000)
    shot(page, "01_dashboard_loaded")
    save_html(page, "01_dashboard")
    print(f"  URL final: {page.url}")
    return True


# ---------------------------------------------------------------------------
# Paso 2: Explorar el dashboard (posicion-global)
# ---------------------------------------------------------------------------

def step_explore_dashboard(page: Page) -> list:
    """Analiza la pantalla de posición global y encuentra las tarjetas de cuentas."""
    print("\n[2] Explorando dashboard (posición global)…")
    dump_elements(page, "Dashboard — todos los botones y links")

    # Buscar tarjetas de cuentas corrientes por texto
    account_candidates = []
    for sel in [
        # Selectores típicos de SPAs de banca
        "[class*='account']", "[class*='cuenta']", "[class*='product']",
        "[class*='card']", "[data-type*='account']",
        "article", "section[class*='item']",
    ]:
        els = page.query_selector_all(sel)
        for el in els:
            try:
                txt = (el.inner_text() or "").lower().strip()
                if any(kw in txt for kw in ["cuenta", "corriente", "saldo", "iban", "disponible"]):
                    if el.is_visible():
                        account_candidates.append(el)
            except Exception:
                pass
        if account_candidates:
            break

    # Fallback: buscar por texto directamente
    if not account_candidates:
        for el in page.query_selector_all("*"):
            try:
                txt = (el.inner_text() or "").lower()
                if "cuenta corriente" in txt and el.is_visible():
                    account_candidates.append(el)
                    if len(account_candidates) >= 5:
                        break
            except Exception:
                pass

    print(f"  Tarjetas de cuenta encontradas: {len(account_candidates)}")
    for i, el in enumerate(account_candidates[:5]):
        try:
            txt = (el.inner_text() or "")[:80].replace("\n", " ").strip()
            cls = (el.get_attribute("class") or "")[:80]
            print(f"    [{i}] text={txt!r} class={cls!r}")
        except Exception:
            pass

    return account_candidates


# ---------------------------------------------------------------------------
# Paso 3: Entrar en una cuenta y navegar a movimientos
# ---------------------------------------------------------------------------

def step_open_account(page: Page, account_candidates: list) -> bool:
    """Hace clic en la primera cuenta corriente y navega a movimientos."""
    print("\n[3] Abriendo la primera cuenta corriente…")

    clicked = False

    # Intentar clic directo en los candidatos
    for el in account_candidates[:3]:
        try:
            if el.is_visible():
                el.click()
                page.wait_for_timeout(3_000)
                wait_for_spa(page, timeout=10_000)
                print(f"  ✓ Clic en tarjeta de cuenta. URL: {page.url}")
                clicked = True
                break
        except Exception as e:
            print(f"  Fallo en clic: {e}")

    # Fallback: navegar directamente al hash de movimientos si la URL cambió
    if not clicked or page.url == "https://web.bbva.es/index.html#posicion-global":
        print("  Intentando navegar por hash routing…")
        for url in [
            "https://web.bbva.es/index.html#mis-cuentas",
            "https://web.bbva.es/index.html#cuentas",
            "https://web.bbva.es/index.html#movimientos",
        ]:
            page.goto(url, wait_until="domcontentloaded", timeout=10_000)
            wait_for_spa(page, timeout=8_000)
            if page.url != LOGIN_URL:
                print(f"  ✓ Cargado: {page.url}")
                break

    shot(page, "02_account_or_cuentas")
    save_html(page, "02_account_or_cuentas")
    dump_elements(page, "Tras abrir cuenta")
    return True


# ---------------------------------------------------------------------------
# Paso 4: Navegar a movimientos dentro de la cuenta
# ---------------------------------------------------------------------------

def step_navigate_to_movements(page: Page):
    print("\n[4] Navegando a movimientos…")

    movement_selectors = [
        "a:has-text('Movimientos')",
        "button:has-text('Movimientos')",
        "a:has-text('movimientos')",
        "[aria-label*='Movimientos']",
        "[aria-label*='movimientos']",
        "a[href*='movimiento']",
        "li:has-text('Movimientos')",
        "span:has-text('Movimientos')",
        # Tabs típicas de SPAs BBVA
        "[role='tab']:has-text('Movimientos')",
        "[role='tab']:has-text('movimientos')",
    ]

    for sel in movement_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"  ✓ Movimientos con: {sel}")
                el.click()
                wait_for_spa(page, timeout=10_000)
                shot(page, "03_movements")
                save_html(page, "03_movements")
                dump_elements(page, "Pantalla de movimientos")
                return True
        except Exception:
            pass

    print("  ✗ No se encontró pestaña de movimientos directamente.")
    print("    Volcando TODOS los elementos para análisis…")
    dump_elements(page, "Búsqueda de movimientos — todos", "button, a, [role='tab'], li, span[class*='tab']", 60)
    shot(page, "03_movements_search_failed")
    save_html(page, "03_movements_search_failed")
    return False


# ---------------------------------------------------------------------------
# Paso 5: Localizar y pulsar el botón de descarga/exportación
# ---------------------------------------------------------------------------

def step_download_movements(page: Page):
    print("\n[5] Buscando botón de descarga/exportación…")
    shot(page, "04_before_download")

    # Selectores específicos para el excelmaker de BBVA y botones genéricos
    download_selectors = [
        # Por aria-label (lo más robusto en SPAs)
        "button[aria-label*='descargar']",
        "button[aria-label*='Descargar']",
        "button[aria-label*='exportar']",
        "button[aria-label*='Exportar']",
        "button[aria-label*='Excel']",
        "button[aria-label*='CSV']",
        # Por clase (BBVA usa iconos de fuente)
        "button[class*='download']",
        "button[class*='export']",
        "[class*='c-icon-download']",
        "[class*='c-icon-export']",
        # Por texto
        "button:has-text('Descargar')",
        "button:has-text('Exportar')",
        "button:has-text('Excel')",
        "button:has-text('CSV')",
        # Links con href de descarga
        "a[href*='csv']", "a[href*='excel']", "a[href*='xls']", "a[download]",
        # Iconos dentro de botones (BBVA usa c-icon-* como clases en <i>)
        "button:has(i[class*='download'])",
        "button:has(i[class*='export'])",
        "button:has([class*='c-icon-download'])",
        "button:has(svg[class*='download'])",
    ]

    found = []
    for sel in download_selectors:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    txt = (el.inner_text() or "")[:60].strip()
                    cls = (el.get_attribute("class") or "")[:80]
                    aria = el.get_attribute("aria-label") or ""
                    print(f"  ✓ Candidato: {sel!r} aria-label={aria!r} text={txt!r} class={cls!r}")
                    found.append((sel, el))
        except Exception:
            pass

    if not found:
        print("  ✗ No se encontró botón de descarga con selectores conocidos.")
        print("    Mostrando TODOS los botones para análisis manual…")
        dump_elements(page, "Todos los botones", "button, [role='button']", 60)
        return

    # Intentar clic en el primero encontrado
    sel, el = found[0]
    print(f"\n  Haciendo clic en: {sel!r}")
    try:
        with page.expect_download(timeout=15_000) as dl_info:
            el.click()
        dl = dl_info.value
        dest = OUT_DIR / f"extracto_{dl.suggested_filename}"
        dl.save_as(str(dest))
        print(f"  ✅ Archivo descargado: {dest}")
        print(f"     Tipo: {dl.suggested_filename}")
    except Exception as e:
        print(f"  Sin descarga directa ({e}), capturando estado post-clic…")
        page.wait_for_timeout(4_000)
        shot(page, "05_after_download_click")
        save_html(page, "05_after_download_click")
        dump_elements(page, "Tras clic de descarga — modal/menú desplegado")
        # Puede haberse abierto un modal de selección de formato
        _handle_format_modal(page)


def _handle_format_modal(page: Page):
    """Si al clicar descarga se abre un modal de selección de formato, elige Excel o CSV."""
    print("\n  Buscando modal de selección de formato…")
    for sel in [
        "button:has-text('Excel')",
        "button:has-text('CSV')",
        "button:has-text('xlsx')",
        "button:has-text('csv')",
        "[role='dialog'] button",
        "[class*='modal'] button",
        "[class*='overlay'] button",
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                txt = (el.inner_text() or "").strip()
                print(f"  ✓ Opción de formato encontrada: {sel!r} text={txt!r}")
                with page.expect_download(timeout=15_000) as dl_info:
                    el.click()
                dl = dl_info.value
                dest = OUT_DIR / f"extracto_{dl.suggested_filename}"
                dl.save_as(str(dest))
                print(f"  ✅ Descargado tras selección de formato: {dest}")
                return
        except Exception:
            pass

    print("  ✗ No se encontró modal de formato.")
    shot(page, "06_no_format_modal")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print(f"Resultados en: {OUT_DIR}\n")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                channel="chrome", headless=False, slow_mo=400, args=STEALTH_ARGS
            )
            print("✓ Google Chrome del sistema")
        except Exception:
            browser = p.chromium.launch(
                headless=False, slow_mo=400, args=STEALTH_ARGS
            )
            print("⚠ Chromium (Chrome no disponible)")

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

        # Interceptar requests de descarga relevantes
        def on_request(req):
            url = req.url.lower()
            if any(k in url for k in ("excel", "csv", "xls", "export", "descarga", "extracto")):
                entry = {"method": req.method, "url": req.url}
                download_requests.append(entry)
                print(f"  ⬇ {req.method} {req.url[:120]}")
        page.on("request", on_request)

        # ── Flujo ──────────────────────────────────────────────────────────
        if not step_login(page):
            print("\n❌ Login fallido. Comprueba credenciales.")
            page.wait_for_timeout(20_000)
            browser.close()
            return

        account_candidates = step_explore_dashboard(page)
        step_open_account(page, account_candidates)
        step_navigate_to_movements(page)
        step_download_movements(page)

        # Guardar requests interceptadas
        if download_requests:
            rpt = OUT_DIR / "download_requests.json"
            rpt.write_text(json.dumps(download_requests, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"\n📋 {len(download_requests)} requests de descarga en: {rpt}")
            for r in download_requests:
                print(f"  {r['method']} {r['url'][:120]}")

        print(f"\n✅ Exploración completada. Screenshots en: {OUT_DIR}")
        print("   Navegador abierto 30 s para inspección manual…")
        page.wait_for_timeout(30_000)
        browser.close()


if __name__ == "__main__":
    main()
