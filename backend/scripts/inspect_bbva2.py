"""
Inspección dirigida de BBVA — segunda pasada.

Objetivos:
  1. Bypasear la detección de bots usando Chrome real (channel='chrome')
     y sin marcas de automatización (args de stealth).
  2. Inspeccionar el iframe de login en nimbus/signin.html.
  3. Identificar los selectores exactos del formulario.

Uso:
    cd backend
    /usr/local/bin/python3 scripts/inspect_bbva2.py
"""

import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from playwright.sync_api import sync_playwright

OUT_DIR = Path("/tmp/bbva2_inspect")
OUT_DIR.mkdir(parents=True, exist_ok=True)

BBVA_USER = os.environ.get("BBVA_JGB_USER", "")
BBVA_PASS = os.environ.get("BBVA_JGB_PASSWORD", "")

if not BBVA_USER or not BBVA_PASS:
    print("ERROR: Define BBVA_JGB_USER y BBVA_JGB_PASSWORD en backend/.env")
    sys.exit(1)

# Argumentos para reducir la huella de automatización
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--start-maximized",
]


def shot(page, name):
    p = OUT_DIR / f"{name}.png"
    page.screenshot(path=str(p), full_page=False)  # solo viewport para ver el estado visible
    print(f"  📸 {p}")


def dump_frames(page, label):
    print(f"\n--- {label} ---")
    print(f"  URL principal: {page.url}")
    print(f"  Frames totales: {len(page.frames)}")
    for i, frame in enumerate(page.frames):
        url = frame.url
        print(f"\n  [Frame {i}] {url}")
        els = frame.query_selector_all("input, button")
        for el in els[:20]:
            try:
                tag  = el.evaluate("e => e.tagName.toLowerCase()")
                t    = el.get_attribute("type") or ""
                name = el.get_attribute("name") or ""
                id_  = el.get_attribute("id") or ""
                ph   = el.get_attribute("placeholder") or ""
                cls  = (el.get_attribute("class") or "")[:60]
                txt  = (el.inner_text() or "")[:40].strip()
                vis  = el.is_visible()
                print(f"    <{tag} type={t!r} name={name!r} id={id_!r} "
                      f"placeholder={ph!r} text={txt!r} visible={vis} class={cls!r}>")
            except Exception:
                pass


def main():
    with sync_playwright() as p:
        # Intentar con Chrome real instalado en el sistema
        # Si no está disponible, caer en Chromium con args de stealth
        try:
            browser = p.chromium.launch(
                channel="chrome",   # usa Chrome instalado en el sistema
                headless=False,
                slow_mo=400,
                args=STEALTH_ARGS,
            )
            print("✓ Usando Google Chrome del sistema")
        except Exception:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=400,
                args=STEALTH_ARGS,
            )
            print("⚠ Chrome no disponible, usando Chromium con stealth args")

        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="es-ES",
        )

        # Ocultar webdriver flag via JS
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page = ctx.new_page()

        # ── 1. Homepage ────────────────────────────────────────────────────
        print("\n[1] Cargando BBVA homepage…")
        page.goto("https://www.bbva.es/personas.html", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        shot(page, "01_homepage")

        # ── 2. Aceptar cookies ─────────────────────────────────────────────
        print("\n[2] Aceptando cookies…")
        for sel in [
            ".cookiesgdpr__acceptbtn",
            "button:has-text('Aceptar')",
        ]:
            try:
                page.click(sel, timeout=4000)
                print(f"  ✓ Cookies con: {sel}")
                page.wait_for_timeout(1000)
                break
            except Exception:
                pass

        # ── 3. Ir directamente al login (URL descubierta en primera pasada) ─
        print("\n[3] Navegando directamente a nimbus/signin.html…")
        page.goto("https://www.bbva.es/nimbus/signin.html", wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        shot(page, "02_signin_page")
        dump_frames(page, "Página de signin — todos los frames")

        # ── 4. Intentar rellenar credenciales en frame principal e iframes ──
        print("\n[4] Buscando inputs en todos los frames…")
        filled_user = False
        target_frame = None

        for frame in page.frames:
            for sel in [
                "input[type='text']", "input[name*='user']", "input[id*='user']",
                "input[placeholder*='usuario']", "input[placeholder*='DNI']",
                "input[autocomplete='username']",
            ]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        frame.fill(sel, BBVA_USER)
                        print(f"  ✓ Usuario rellenado en frame [{frame.url}] con: {sel}")
                        filled_user = True
                        target_frame = frame
                        break
                except Exception:
                    pass
            if filled_user:
                break

        if not filled_user:
            print("  ✗ No se pudo rellenar el usuario — el formulario puede ser Shadow DOM")
            print("  Intentando con Shadow DOM piercing…")
            for sel in [
                "input[type='text'] >> visible=true",
                "css=input[type='text']",
            ]:
                try:
                    page.locator(sel).first.fill(BBVA_USER, timeout=3000)
                    print(f"  ✓ Usuario rellenado (locator): {sel}")
                    filled_user = True
                    break
                except Exception:
                    pass

        shot(page, "03_after_user_fill")

        # ── 5. Contraseña ──────────────────────────────────────────────────
        print("\n[5] Buscando campo de contraseña…")
        for frame in page.frames:
            for sel in ["input[type='password']", "input[name*='pass']", "input[id*='pass']"]:
                try:
                    el = frame.query_selector(sel)
                    if el and el.is_visible():
                        frame.fill(sel, BBVA_PASS)
                        print(f"  ✓ Contraseña en frame [{frame.url}] con: {sel}")
                        break
                except Exception:
                    pass

        shot(page, "04_after_pass_fill")

        # ── 6. Ver si hay teclado virtual ─────────────────────────────────
        print("\n[6] Buscando teclado virtual…")
        for frame in page.frames:
            kbd_candidates = frame.query_selector_all(
                "[class*='keyboard'], [class*='teclado'], [data-digit], [class*='key']"
            )
            if kbd_candidates:
                print(f"  Teclado virtual encontrado en frame [{frame.url}]: {len(kbd_candidates)} elementos")
                for el in kbd_candidates[:10]:
                    cls = (el.get_attribute("class") or "")[:60]
                    data = el.get_attribute("data-digit") or el.get_attribute("data-key") or ""
                    txt = (el.inner_text() or "")[:20].strip()
                    print(f"    class={cls!r} data-digit={data!r} text={txt!r}")

        print(f"\n✅ Screenshots en: {OUT_DIR}")
        print("   Navegador abierto 25 s para inspección manual…")
        page.wait_for_timeout(25000)
        browser.close()


if __name__ == "__main__":
    main()
