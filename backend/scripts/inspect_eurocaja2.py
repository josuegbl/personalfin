"""
Inspección dirigida de Eurocaja Rural — segunda pasada.

Objetivo: encontrar la URL real del portal bancario pulsando "ACCESO CLIENTES"
e identificar los selectores del formulario de login.

Uso:
    cd backend
    /usr/local/bin/python3 scripts/inspect_eurocaja2.py
"""

import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from playwright.sync_api import sync_playwright

OUT_DIR = Path("/tmp/eurocaja2_inspect")
OUT_DIR.mkdir(parents=True, exist_ok=True)

EC_USER = os.environ.get("EUROCAJA_USER", "")
EC_PASS = os.environ.get("EUROCAJA_PASSWORD", "")

if not EC_USER or not EC_PASS:
    print("ERROR: Define EUROCAJA_USER y EUROCAJA_PASSWORD en backend/.env")
    sys.exit(1)


def shot(page, name):
    p = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=True)
    print(f"  📸 {p}")


def dump_inputs(page, label):
    print(f"\n--- {label} ---")
    print(f"  URL: {page.url}")
    # También inspeccionar iframes
    for i, frame in enumerate(page.frames):
        if frame == page.main_frame:
            continue
        print(f"  [iframe {i}] src={frame.url}")
        for el in frame.query_selector_all("input, button")[:15]:
            tag  = el.evaluate("e => e.tagName.toLowerCase()")
            t    = el.get_attribute("type") or ""
            name = el.get_attribute("name") or ""
            id_  = el.get_attribute("id") or ""
            ph   = el.get_attribute("placeholder") or ""
            txt  = (el.inner_text() or "")[:40].strip()
            print(f"    <{tag} type={t!r} name={name!r} id={id_!r} placeholder={ph!r} text={txt!r}>")

    for el in page.query_selector_all("input, button, select")[:20]:
        tag  = el.evaluate("e => e.tagName.toLowerCase()")
        t    = el.get_attribute("type") or ""
        name = el.get_attribute("name") or ""
        id_  = el.get_attribute("id") or ""
        ph   = el.get_attribute("placeholder") or ""
        cls  = (el.get_attribute("class") or "")[:60]
        txt  = (el.inner_text() or "")[:40].strip()
        print(f"  <{tag} type={t!r} name={name!r} id={id_!r} placeholder={ph!r} text={txt!r} class={cls!r}>")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── 1. Ir a la página de banca online ─────────────────────────────
        print("\n[1] Cargando www.eurocajarural.es/banca-online/ …")
        page.goto("https://www.eurocajarural.es/banca-online/", wait_until="commit")
        shot(page, "01_inicio")

        # ── 2. Aceptar cookies ─────────────────────────────────────────────
        print("\n[2] Aceptando cookies…")
        for sel in [
            "button:has-text('Sí, acepto todas las cookies')",
            "button:has-text('Aceptar')",
            "button:has-text('Accept')",
        ]:
            try:
                page.click(sel, timeout=3000)
                print(f"  ✓ Cookies aceptadas con: {sel}")
                page.wait_for_timeout(800)
                break
            except Exception:
                pass

        # ── 3. Pulsar "ACCESO CLIENTES" ────────────────────────────────────
        print("\n[3] Pulsando 'ACCESO CLIENTES'…")
        shot(page, "02_pre_acceso")

        # Capturar la nueva pestaña si el botón abre una ventana nueva
        with ctx.expect_page() as new_page_info:
            try:
                page.click("a:has-text('ACCESO CLIENTES'), button:has-text('ACCESO CLIENTES')", timeout=5000)
                print("  ✓ Clic en ACCESO CLIENTES")
            except Exception as e:
                print(f"  Selector directo falló ({e}), buscando href…")
                # Buscar el link por href
                links = page.query_selector_all("a")
                for link in links:
                    txt = (link.inner_text() or "").strip().upper()
                    href = link.get_attribute("href") or ""
                    if "ACCESO" in txt or "CLIENTES" in txt or "ruralvia" in href.lower() or "login" in href.lower():
                        print(f"  Encontrado: text={txt!r} href={href!r}")
                        link.click()
                        break

        # Obtener la nueva pestaña (si se abrió)
        try:
            portal_page = new_page_info.value
            portal_page.wait_for_load_state("domcontentloaded", timeout=15000)
            print(f"  Nueva pestaña abierta: {portal_page.url}")
        except Exception:
            portal_page = page  # Si no abrió nueva pestaña, seguir en la misma

        shot(portal_page, "03_portal_login")
        dump_inputs(portal_page, "Portal bancario")

        # ── 4. Intentar rellenar credenciales ──────────────────────────────
        print("\n[4] Intentando rellenar usuario…")
        filled_user = False
        for sel in [
            "input[name='userId']", "input[id='userId']",
            "input[name='user']",   "input[id='user']",
            "input[name='username']", "input[id='username']",
            "input[type='text']",
            "input[placeholder*='usuario']", "input[placeholder*='Usuario']",
            "input[autocomplete='username']",
        ]:
            try:
                el = portal_page.query_selector(sel)
                if el and el.is_visible():
                    portal_page.fill(sel, EC_USER)
                    print(f"  ✓ Usuario rellenado con: {sel}")
                    filled_user = True
                    break
            except Exception:
                pass

        # Buscar en iframes si no se encontró en el frame principal
        if not filled_user:
            print("  No encontrado en frame principal — buscando en iframes…")
            for frame in portal_page.frames:
                if frame == portal_page.main_frame:
                    continue
                print(f"  Probando iframe: {frame.url}")
                for sel in ["input[type='text']", "input[name*='user']", "input[id*='user']"]:
                    try:
                        el = frame.query_selector(sel)
                        if el and el.is_visible():
                            frame.fill(sel, EC_USER)
                            print(f"  ✓ Usuario rellenado en iframe con: {sel}")
                            filled_user = True
                            break
                    except Exception:
                        pass
                if filled_user:
                    break

        shot(portal_page, "04_user_filled")

        print("\n[5] Intentando rellenar contraseña/PIN…")
        for sel in [
            "input[type='password']",
            "input[name='pin']", "input[id='pin']",
            "input[name='password']", "input[id='password']",
            "input[placeholder*='PIN']", "input[placeholder*='contraseña']",
        ]:
            try:
                el = portal_page.query_selector(sel)
                if el and el.is_visible():
                    portal_page.fill(sel, EC_PASS)
                    print(f"  ✓ Contraseña rellenada con: {sel}")
                    break
            except Exception:
                pass

        shot(portal_page, "05_pass_filled")

        print(f"\n✅ Inspección completada. Screenshots en: {OUT_DIR}")
        print("   Navegador abierto 20 s para inspección manual…")
        portal_page.wait_for_timeout(20000)
        browser.close()


if __name__ == "__main__":
    main()
