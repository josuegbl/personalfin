import io
import csv
from decimal import Decimal
from datetime import date, timedelta
from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
from app.services.sync.base import SourceAdapter, RawTransaction
from app.core.config import settings

# RuralVía — plataforma de banca online de Eurocaja Rural
_BASE_URL = "https://www.eurocajarural.es"
_LOGIN_URL = f"{_BASE_URL}/banca-online/"


class EurocajaAdapter(SourceAdapter):
    """
    Sincronización Eurocaja Rural mediante Playwright (plataforma RuralVía).
    Requiere EUROCAJA_USER y EUROCAJA_PASSWORD en .env.
    """

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
        page.goto(_LOGIN_URL, wait_until="networkidle")

        # Acepta cookies si aparece el banner
        try:
            page.click("button#aceptarCookies", timeout=3000)
        except PWTimeout:
            pass

        # Acceder a banca online
        page.click("a[href*='banca-online'], a:has-text('Acceder')", timeout=10000)
        page.wait_for_load_state("networkidle")

        # Formulario de login RuralVía
        page.fill("input[name='userId'], input#userId", settings.EUROCAJA_USER)
        page.fill("input[name='pin'], input#pin", settings.EUROCAJA_PASSWORD)
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_load_state("networkidle")

    # ------------------------------------------------------------------
    # Saldo
    # ------------------------------------------------------------------

    def _extract_balance(self, page: Page) -> Decimal:
        # En RuralVía el saldo de la cuenta corriente aparece en el resumen
        page.goto(f"{_BASE_URL}/banca-online/cuentas/", wait_until="networkidle")

        # Busca el saldo de la cuenta cuyo IBAN coincide con account.iban
        if self.account.iban:
            iban_short = self.account.iban[-4:]
            selector = f"text={iban_short}"
            try:
                row = page.locator(selector).first.locator("..").locator("..")
                raw = row.locator(".saldo, [class*='saldo'], [class*='balance']").inner_text()
                return _parse_amount(raw)
            except Exception:
                pass

        # Fallback: primer saldo visible
        raw = page.locator(".saldo, [class*='saldo'], [class*='balance']").first.inner_text()
        return _parse_amount(raw)

    # ------------------------------------------------------------------
    # Descarga de movimientos (CSV)
    # ------------------------------------------------------------------

    def _download_movements_csv(self, page: Page) -> str:
        fecha_desde = (date.today() - timedelta(days=90)).strftime("%d/%m/%Y")
        fecha_hasta = date.today().strftime("%d/%m/%Y")

        # Navegar a movimientos de la cuenta
        page.goto(f"{_BASE_URL}/banca-online/cuentas/movimientos/", wait_until="networkidle")

        # Seleccionar cuenta si hay más de una (por IBAN)
        if self.account.iban:
            iban_short = self.account.iban[-4:]
            try:
                page.select_option("select[name*='cuenta'], select[id*='cuenta']", label=f"*{iban_short}*")
            except Exception:
                pass

        # Establecer rango de fechas
        date_from = page.locator("input[name*='desde'], input[id*='desde'], input[placeholder*='desde']").first
        date_to   = page.locator("input[name*='hasta'], input[id*='hasta'], input[placeholder*='hasta']").first
        date_from.fill(fecha_desde)
        date_to.fill(fecha_hasta)

        # Buscar / aplicar filtro
        page.click("button:has-text('Buscar'), button:has-text('Ver'), input[value*='Buscar']")
        page.wait_for_load_state("networkidle")

        # Descargar CSV — RuralVía ofrece exportar como CSV/Excel
        with page.expect_download() as dl:
            page.click(
                "a:has-text('CSV'), button:has-text('CSV'), "
                "a:has-text('Exportar'), button:has-text('Exportar'), "
                "a[href*='.csv'], a[href*='export']",
                timeout=10000,
            )
        download = dl.value
        return download.path().read_text(encoding="latin-1")

    # ------------------------------------------------------------------
    # Parseo del CSV de RuralVía
    # ------------------------------------------------------------------

    def _parse_csv(self, content: str) -> list[RawTransaction]:
        """
        El CSV de RuralVía suele tener este formato (separador ';'):
          Fecha Operación;Fecha Valor;Concepto;Importe;Saldo
        Las primeras filas pueden ser cabeceras de metadatos.
        """
        results: list[RawTransaction] = []
        reader = csv.DictReader(
            io.StringIO(content),
            delimiter=";",
        )

        for row in reader:
            fecha_raw   = _get_field(row, "Fecha Operación", "Fecha Mov", "FECHA OPERACION")
            concepto    = _get_field(row, "Concepto", "CONCEPTO", "Descripción")
            importe_raw = _get_field(row, "Importe", "IMPORTE", "Cargo/Abono")

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
    """'1.234,56' → Decimal('1234.56')"""
    cleaned = raw.strip().replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    return Decimal(cleaned)


def _parse_date(raw: str) -> date:
    """'DD/MM/YYYY' → date"""
    from datetime import datetime
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {raw}")
