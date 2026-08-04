import io
import csv
from decimal import Decimal
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
from app.services.sync.base import SourceAdapter, RawTransaction
from app.core.config import settings

_LOGIN_URL = "https://www.bbva.es/personas.html"


class BBVAAdapter(SourceAdapter):
    """
    Sincronización BBVA mediante Playwright.
    Soporta dos cuentas: Josué (propietario='Josué') y Adi (propietario='Adi').
    Credenciales en .env: BBVA_JGB_USER/PASSWORD y BBVA_ADI_USER/PASSWORD.
    """

    def _credentials(self) -> tuple[str, str]:
        if self.account.propietario == "Adi":
            return settings.BBVA_ADI_USER, settings.BBVA_ADI_PASSWORD
        return settings.BBVA_JGB_USER, settings.BBVA_JGB_PASSWORD

    def fetch_balance(self) -> Decimal:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                self._login(page)
                return self._extract_balance(page)
            finally:
                browser.close()

    def fetch_transactions(self) -> list[RawTransaction]:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                self._login(page)
                csv_content = self._download_movements_csv(page)
                return self._parse_csv(csv_content)
            finally:
                browser.close()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def _login(self, page: Page):
        user, password = self._credentials()

        page.goto(_LOGIN_URL, wait_until="networkidle")

        # Aceptar cookies si aparece el banner
        try:
            page.click("#aceptar-cookies, button:has-text('Aceptar')", timeout=3000)
        except PWTimeout:
            pass

        # Abrir el panel de login
        page.click("[data-testid='login-button'], a:has-text('Acceder'), button:has-text('Acceder')")
        page.wait_for_load_state("networkidle")

        # Identificador de usuario
        page.fill(
            "input[name='user'], input[id='user'], input[placeholder*='usuario'], input[placeholder*='DNI']",
            user,
        )
        # Contraseña — BBVA usa un teclado virtual en algunos flujos;
        # intentamos primero campo de texto normal y luego el teclado virtual.
        try:
            page.fill("input[name='password'], input[id='password'], input[type='password']", password)
        except PWTimeout:
            self._fill_virtual_keyboard(page, password)

        page.click("button[type='submit'], [data-testid='login-submit']")
        page.wait_for_load_state("networkidle")

    def _fill_virtual_keyboard(self, page: Page, password: str):
        """Teclado virtual de BBVA: hace clic en cada dígito por orden."""
        for digit in password:
            page.click(f"[data-digit='{digit}'], button:has-text('{digit}')", timeout=5000)

    # ------------------------------------------------------------------
    # Saldo
    # ------------------------------------------------------------------

    def _extract_balance(self, page: Page) -> Decimal:
        # Navegar a la sección de cuentas
        page.goto("https://www.bbva.es/particulares/mis-cuentas.html", wait_until="networkidle")

        # Si la cuenta tiene IBAN, buscar la fila correspondiente
        if self.account.iban:
            iban_short = self.account.iban[-4:]
            try:
                row = page.locator(f"text={iban_short}").first.locator("..").locator("..")
                raw = row.locator("[class*='saldo'], [class*='balance'], [class*='importe']").first.inner_text()
                return _parse_amount(raw)
            except Exception:
                pass

        # Fallback: primer saldo visible de la página
        raw = page.locator("[class*='saldo'], [class*='balance']").first.inner_text()
        return _parse_amount(raw)

    # ------------------------------------------------------------------
    # Descarga de movimientos (CSV / Excel)
    # ------------------------------------------------------------------

    def _download_movements_csv(self, page: Page) -> str:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%d/%m/%Y")
        fecha_hasta = date.today().strftime("%d/%m/%Y")

        # Navegar a movimientos de la cuenta
        page.goto("https://www.bbva.es/particulares/mis-cuentas/movimientos.html", wait_until="networkidle")

        # Seleccionar la cuenta correcta si hay varias
        if self.account.iban:
            iban_short = self.account.iban[-4:]
            try:
                page.select_option(
                    "select[name*='cuenta'], select[id*='cuenta']",
                    label=f"*{iban_short}*",
                )
            except Exception:
                pass

        # Establecer fechas
        for selector, valor in [
            ("input[name*='desde'], input[id*='fechaDesde']", fecha_desde),
            ("input[name*='hasta'], input[id*='fechaHasta']", fecha_hasta),
        ]:
            try:
                page.fill(selector, valor)
            except Exception:
                pass

        # Buscar
        page.click("button:has-text('Buscar'), button[type='submit']")
        page.wait_for_load_state("networkidle")

        # Descargar CSV — BBVA ofrece "Descargar" o "Exportar"
        with page.expect_download() as dl:
            page.click(
                "button:has-text('Descargar'), a:has-text('Descargar'), "
                "button:has-text('Exportar'), a:has-text('Exportar'), "
                "a[href*='.csv'], button:has-text('CSV')",
                timeout=10000,
            )
        return dl.value.path().read_text(encoding="latin-1")

    # ------------------------------------------------------------------
    # Parseo del CSV de BBVA
    # ------------------------------------------------------------------

    def _parse_csv(self, content: str) -> list[RawTransaction]:
        """
        BBVA exporta un CSV (separador ';') con cabecera informativa en las
        primeras filas. Las columnas de datos son:
          Fecha;Fecha valor;Concepto;Movimiento;Disponible
        El importe puede ser positivo (abono) o negativo (cargo).
        """
        results: list[RawTransaction] = []

        # Saltar filas de cabecera hasta encontrar la línea de columnas
        lines = content.splitlines()
        data_start = 0
        for i, line in enumerate(lines):
            if "Fecha" in line and ("Concepto" in line or "Movimiento" in line):
                data_start = i
                break

        reader = csv.DictReader(
            io.StringIO("\n".join(lines[data_start:])),
            delimiter=";",
        )

        for row in reader:
            fecha_raw   = _get_field(row, "Fecha", "FECHA")
            concepto    = _get_field(row, "Concepto", "CONCEPTO", "Descripción")
            importe_raw = _get_field(row, "Movimiento", "Importe", "IMPORTE", "Cargo/Abono")

            if not fecha_raw or not importe_raw:
                continue

            try:
                fecha   = _parse_date(fecha_raw)
                importe = _parse_amount(importe_raw)
            except (ValueError, ArithmeticError):
                continue

            results.append(RawTransaction(
                fecha=fecha,
                importe=importe,
                concepto=concepto or "",
            ))

        return results


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_field(row: dict, *keys: str) -> str | None:
    for k in keys:
        v = row.get(k, "").strip()
        if v:
            return v
    return None


def _parse_amount(raw: str) -> Decimal:
    """'1.234,56' o '-1.234,56' → Decimal"""
    cleaned = raw.strip().replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    return Decimal(cleaned)


def _parse_date(raw: str) -> date:
    from datetime import datetime
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {raw}")
