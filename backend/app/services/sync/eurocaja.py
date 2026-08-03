from decimal import Decimal
from app.services.sync.base import SourceAdapter, RawTransaction
from app.core.config import settings


class EurocajaAdapter(SourceAdapter):
    """
    Sincronización Eurocaja Rural mediante Playwright.
    Requiere credenciales en .env: EUROCAJA_USER, EUROCAJA_PASSWORD.
    """

    def fetch_balance(self) -> Decimal:
        return Decimal("0")

    def fetch_transactions(self) -> list[RawTransaction]:
        return []
