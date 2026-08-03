import httpx
from decimal import Decimal
from datetime import date, timedelta
from app.services.sync.base import SourceAdapter, RawTransaction
from app.models.transaction import TransactionOrigin
from app.core.config import settings

PAYPAL_SANDBOX = "https://api-m.sandbox.paypal.com"
PAYPAL_LIVE = "https://api-m.paypal.com"


class PayPalAdapter(SourceAdapter):
    """
    Sincronización PayPal mediante REST API v2 (OAuth 2.0 client credentials).
    Requiere PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET en .env.
    """

    def _base_url(self) -> str:
        return PAYPAL_SANDBOX if settings.PAYPAL_MODE == "sandbox" else PAYPAL_LIVE

    def _get_token(self) -> str:
        resp = httpx.post(
            f"{self._base_url()}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_balance(self) -> Decimal:
        token = self._get_token()
        resp = httpx.get(
            f"{self._base_url()}/v1/reporting/balances",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        # Buscar saldo EUR disponible
        for bal in data.get("balances", []):
            if bal.get("currency_code") == "EUR" and bal.get("type") == "AVAILABLE":
                return Decimal(bal["total_balance"]["value"])
        return Decimal("0.00")

    def fetch_transactions(self) -> list[RawTransaction]:
        token = self._get_token()
        start = (date.today() - timedelta(days=30)).isoformat() + "T00:00:00-0000"
        end = date.today().isoformat() + "T23:59:59-0000"

        resp = httpx.get(
            f"{self._base_url()}/v1/reporting/transactions",
            params={
                "start_date": start,
                "end_date": end,
                "fields": "all",
                "page_size": 500,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()

        results = []
        for item in resp.json().get("transaction_details", []):
            info = item.get("transaction_info", {})
            amount = info.get("transaction_amount", {})
            if not amount:
                continue

            importe = Decimal(amount.get("value", "0"))
            if importe == 0:
                continue

            payer = item.get("payer_info", {})
            comercio = (
                payer.get("payer_name", {}).get("alternate_full_name")
                or info.get("transaction_subject")
            )

            results.append(
                RawTransaction(
                    fecha=date.fromisoformat(info["transaction_initiation_date"][:10]),
                    importe=importe,
                    concepto=info.get("transaction_note") or info.get("transaction_subject") or "PayPal",
                    comercio=comercio,
                    origen=TransactionOrigin.paypal,
                    paypal_transaction_id=info.get("transaction_id"),
                )
            )
        return results
