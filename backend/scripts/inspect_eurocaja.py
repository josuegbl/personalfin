"""
Script de inspección del DOM de Eurocaja Rural (plataforma RuralVía).

Abre el navegador en modo VISIBLE para identificar los selectores reales
del login y la descarga de movimientos.

Uso:
    cd backend
    python scripts/inspect_eurocaja.py

Necesita EUROCAJA_USER y EUROCAJA_PASSWORD en .env.
Genera screenshots en /tmp/eurocaja_inspect/ y vuelca el HTML de cada paso.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from playwright.sync_api import sync_playwright

OUT_DIR = Path("/tmp/eurocaja_inspect")
OUT_DIR.mkdir(parents=True, exist_ok=True)

EC_USER = os.environ.get("EUROCAJA_USER", "")
EC_PASS = os.environ.get("EUROCAJA_PASSWORD", "")

if not EC_USER or not EC_PASS:
    print("ERROR: Define EUROCAJA_USER y EUROCAJA_PASSWORD en backend/.env")
    sys.exit(1)

# URLs candidatas a probar — RuralVía es una plataforma compartida por múltiples
# cajas rurales. La URL exacta varía por entidad.
LOGIN_URLS = [
    "https://eurocajarural.ruralvia.com/",
    "https://www.ruralvia.com/",
    "https://www.eurocajarural.es/banca-online/",
    "https://banca.eurocajarural.es/",
]


def shot(page, name: str):
    path = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  📸 Screenshot: {path}")


def dump_inputs(page, label: str):
    print(f"\n--- {label} ---")
    print("URL:", page.url)
    inputs = page.query_selector_all("input, button, select, form")
    for el in inputs[:30]:
        tag   = el.evaluate("e => e.tagName.toLowerCase()")
        type_ = el.get_attribute("type") or ""
        name  = el.get_attribute("name") or ""
        id_   = el.get_attribute("id") or ""
        cls   = (el.get_attribute("class") or "")[:60]
        ph    = el.get_attribute("placeholder") or ""
        text  = (el.inner_text() or "")[:40].replace("\n", " ").strip()
        data  = {k: v for k, v in (el.evaluate(
            "e => Object.fromEntries([...e.attributes].map(a => [a.name, a.value]))"
        ) or {}).items() if k.startswith("data-")}
        print(
            f"  <{tag} type={type_!r:10} name={name!r:25} id={id_!r:25} "
            f"placeholder={ph!r:30} text={text!r:35} data={data} class={cls!r}>"
        )


def try_login_url(page, url: str) -> bool:
    """Intenta cargar la URL. Devuelve True si parece una página de login."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        print(f"  ✓ Cargado: {page.url}")
        return True
    except Exception as e:
        print(f"  ✗ Error cargando {url}: {e}")
        return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── Paso 1: Encontrar la URL de login real ────────────────────────
        print("\n[1] Probando URLs candidatas de Eurocaja Rural / RuralVía…")
        login_found = False
        for i, url in enumerate(LOGIN_URLS):
            print(f"\n  Probando: {url}")
            if try_login_url(page, url):
                shot(page, f"01_url_{i:02d}_{url.split('/')[2]}")
                dump_inputs(page, f"URL candidata: {url}")
                # Preguntar si parece el portal correcto
                has_form = len(page.query_selector_all("input[type='password'], input[type='text']")) > 0
                print(f"  ¿Tiene formulario de login? {'SÍ' if has_form else 'NO'}")
                if has_form:
                    login_found = True
                    print(f"  → URL de login encontrada: {page.url}")
                    break

        if not login_found:
            print("\n  Ninguna URL candidata tenía formulario. Comprueba manualmente.")
            print("  El navegador quedará abierto 60 s…")
            page.wait_for_timeout(60000)
            browser.close()
            return

        # ── Paso 2: Aceptar cookies ───────────────────────────────────────
        print("\n[2] Buscando banner de cookies…")
        for sel in ["button#aceptarCookies", "button:has-text('Aceptar')",
                    "button:has-text('Accept')", "[id*='cookie'] button",
                    "button:has-text('Entendido')"]:
            try:
                page.click(sel, timeout=3000)
                print(f"  Cookie aceptado con: {sel}")
                page.wait_for_timeout(500)
                break
            except Exception:
                pass

        # ── Paso 3: Rellenar credenciales ─────────────────────────────────
        print("\n[3] Intentando rellenar usuario…")
        for sel in [
            "input[name='userId']", "input[id='userId']",
            "input[name='user']", "input[id='user']",
            "input[name='username']", "input[id='username']",
            "input[type='text']", "input[autocomplete='username']",
            "input[placeholder*='usuario']", "input[placeholder*='Usuario']",
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    page.fill(sel, EC_USER, timeout=3000)
                    print(f"  Usuario rellenado con: {sel}")
                    break
            except Exception:
                pass

        shot(page, "03_user_filled")

        print("\n[4] Intentando rellenar contraseña / PIN…")
        for sel in [
            "input[name='pin']", "input[id='pin']",
            "input[type='password']",
            "input[name='password']", "input[id='password']",
            "input[placeholder*='contraseña']", "input[placeholder*='PIN']",
            "input[autocomplete='current-password']",
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    page.fill(sel, EC_PASS, timeout=3000)
                    print(f"  Contraseña/PIN rellenado con: {sel}")
                    break
            except Exception:
                pass

        shot(page, "04_pass_filled")
        dump_inputs(page, "Formulario relleno")

        # ── Paso 4: Submit ────────────────────────────────────────────────
        print("\n[5] Submit del formulario…")
        for sel in [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Entrar')",
            "button:has-text('Acceder')",
            "button:has-text('Identificarme')",
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    page.click(sel, timeout=4000)
                    print(f"  Submit con: {sel}")
                    break
            except Exception:
                pass

        print("  Esperando tras submit (10 s)…")
        page.wait_for_timeout(10000)
        shot(page, "05_post_login")
        dump_inputs(page, "Tras login")
        print(f"\n  URL tras login: {page.url}")

        # ── Paso 5: Navegar a movimientos ─────────────────────────────────
        print("\n[6] Buscando sección de movimientos…")
        shot(page, "06_banca_home")
        dump_inputs(page, "Home banca online")

        # Buscar links a movimientos / cuentas
        links = page.query_selector_all("a")
        for link in links[:50]:
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").strip()[:50]
            if any(kw in text.lower() or kw in href.lower()
                   for kw in ["movimiento", "cuenta", "extracto", "saldo"]):
                print(f"  Link relevante: text={text!r} href={href!r}")

        print(f"\n✅ Inspección completada. Revisa los screenshots en: {OUT_DIR}")
        print("   El navegador quedará abierto 15 s para inspección manual…")
        page.wait_for_timeout(15000)
        browser.close()


if __name__ == "__main__":
    main()
