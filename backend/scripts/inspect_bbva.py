"""
Script de inspección del DOM de BBVA.

Abre el navegador en modo VISIBLE para que puedas ver exactamente qué renderiza
BBVA en cada paso del login y la descarga de movimientos.

Uso:
    cd backend
    python scripts/inspect_bbva.py

Necesita las credenciales en .env (BBVA_CUENTA_A_USER / BBVA_CUENTA_A_PASSWORD).
Genera screenshots en /tmp/bbva_inspect/ y vuelca el HTML de cada paso.
"""

import os
import sys
from pathlib import Path
from datetime import date, timedelta

# Añadir el directorio raíz al path para poder importar app.core.config
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from playwright.sync_api import sync_playwright

OUT_DIR = Path("/tmp/bbva_inspect")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BBVA_USER = os.environ.get("BBVA_CUENTA_A_USER", "")
BBVA_PASS = os.environ.get("BBVA_CUENTA_A_PASSWORD", "")

if not BBVA_USER or not BBVA_PASS:
    print("ERROR: Define BBVA_CUENTA_A_USER y BBVA_CUENTA_A_PASSWORD en backend/.env")
    sys.exit(1)


def shot(page, name: str):
    path = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  📸 Screenshot: {path}")


def dump_inputs(page, label: str):
    """Imprime todos los inputs/buttons visibles para identificar selectores."""
    print(f"\n--- {label} ---")
    print("URL:", page.url)
    inputs = page.query_selector_all("input, button, select, textarea, a[href]")
    for el in inputs[:30]:  # limitar a 30 para no saturar
        tag  = el.evaluate("e => e.tagName.toLowerCase()")
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


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── Paso 1: Homepage ──────────────────────────────────────────────
        print("\n[1] Navegando a BBVA homepage…")
        page.goto("https://www.bbva.es/personas.html", wait_until="domcontentloaded", timeout=30000)
        shot(page, "01_homepage")
        dump_inputs(page, "Homepage")

        # ── Paso 2: Aceptar cookies ───────────────────────────────────────
        print("\n[2] Buscando banner de cookies…")
        for sel in ["#aceptar-cookies", "button:has-text('Aceptar')", "button:has-text('Accept')",
                    "[id*='accept']", "[id*='cookie']"]:
            try:
                page.click(sel, timeout=3000)
                print(f"  Cookie banner aceptado con selector: {sel}")
                page.wait_for_timeout(1000)
                break
            except Exception:
                pass

        # ── Paso 3: Buscar botón de Acceder ──────────────────────────────
        print("\n[3] Buscando botón de Acceder / login…")
        shot(page, "02_pre_login_click")
        dump_inputs(page, "Antes de hacer clic en Acceder")

        for sel in [
            "[data-testid='login-button']",
            "a:has-text('Acceder')",
            "button:has-text('Acceder')",
            "a[href*='banca-online']",
            "a[href*='login']",
        ]:
            try:
                page.click(sel, timeout=4000)
                print(f"  Clic en Acceder con: {sel}")
                page.wait_for_load_state("domcontentloaded")
                break
            except Exception:
                pass

        shot(page, "03_after_acceder_click")
        dump_inputs(page, "Después de clic en Acceder")

        # ── Paso 4: Rellenar usuario ──────────────────────────────────────
        print("\n[4] Intentando rellenar usuario…")
        for sel in [
            "input[name='user']", "input[id='user']",
            "input[placeholder*='usuario']", "input[placeholder*='DNI']",
            "input[placeholder*='Usuario']", "input[type='text']",
            "input[autocomplete='username']",
        ]:
            try:
                page.fill(sel, BBVA_USER, timeout=3000)
                print(f"  Usuario rellenado con: {sel}")
                break
            except Exception:
                pass

        shot(page, "04_user_filled")

        # ── Paso 5: Rellenar contraseña ───────────────────────────────────
        print("\n[5] Intentando rellenar contraseña…")
        for sel in [
            "input[type='password']",
            "input[name='password']", "input[id='password']",
            "input[placeholder*='contraseña']", "input[placeholder*='Contraseña']",
            "input[autocomplete='current-password']",
        ]:
            try:
                page.fill(sel, BBVA_PASS, timeout=3000)
                print(f"  Contraseña rellenada con: {sel}")
                break
            except Exception:
                pass

        shot(page, "05_password_filled")
        dump_inputs(page, "Formulario login relleno")

        # ── Paso 6: Submit ────────────────────────────────────────────────
        print("\n[6] Submit del formulario…")
        for sel in [
            "button[type='submit']",
            "[data-testid='login-submit']",
            "button:has-text('Entrar')",
            "button:has-text('Acceder')",
            "input[type='submit']",
        ]:
            try:
                page.click(sel, timeout=4000)
                print(f"  Submit con: {sel}")
                break
            except Exception:
                pass

        print("  Esperando carga tras submit (10 s)…")
        page.wait_for_timeout(10000)
        shot(page, "06_post_login")
        dump_inputs(page, "Tras submit de login")
        print(f"\n  URL final: {page.url}")

        # ── Paso 7: Página de cuentas ────────────────────────────────────
        print("\n[7] Intentando navegar a movimientos…")
        for url in [
            "https://www.bbva.es/general/banca-online/banca-online.html",
            "https://www.bbva.es/particulares/mis-cuentas.html",
            "https://www.bbva.es/particulares/mis-cuentas/movimientos.html",
        ]:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                print(f"  Cargado: {url}")
                shot(page, f"07_movimientos_{url.split('/')[-1].replace('.html','')}")
                dump_inputs(page, f"Página {url}")
                break
            except Exception as e:
                print(f"  Fallo con {url}: {e}")

        print(f"\n✅ Inspección completada. Revisa los screenshots en: {OUT_DIR}")
        print("   El navegador quedará abierto 15 s para inspección manual…")
        page.wait_for_timeout(15000)
        browser.close()


if __name__ == "__main__":
    main()
