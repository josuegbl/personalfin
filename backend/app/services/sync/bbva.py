from decimal import Decimal
from app.services.sync.base import SourceAdapter, RawTransaction
from app.core.config import settings


class BBVAAdapter(SourceAdapter):
    """
    Sincronización BBVA mediante Playwright.
    Requiere credenciales en .env: BBVA_USER, BBVA_PASSWORD.
    """

    def fetch_balance(self) -> Decimal:
        # TODO: implementar scraping con Playwright
        # Flujo: login → página de cuentas → extraer saldo
        raise NotImplementedError("BBVAAdapter.fetch_balance pendiente de implementación")

    def fetch_transactions(self) -> list[RawTransaction]:
        # TODO: implementar scraping con Playwright
        # Flujo: login → movimientos → descargar últimos 30 días
        raise NotImplementedError("BBVAAdapter.fetch_transactions pendiente de implementación")

    def _login(self, page):
        page.goto("https://www.bbva.es/personas.html")
        page.click("[data-testid='login-button']")
        page.fill("[name='user']", settings.BBVA_USER)
        page.fill("[name='password']", settings.BBVA_PASSWORD)
        page.click("[type='submit']")
        page.wait_for_load_state("networkidle")
