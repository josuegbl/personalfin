import httpx
from decimal import Decimal
from datetime import date, timedelta, timezone, datetime
from app.services.sync.base import SourceAdapter, RawTransaction
from app.models.transaction import TransactionOrigin
from app.core.config import settings

PAYPAL_SANDBOX = "https://api-m.sandbox.paypal.com"
PAYPAL_LIVE    = "https://api-m.paypal.com"

# Importes de PayPal en cuentas bancarias llevan estos textos en el concepto
_PASSTHROUGH_KEYWORDS = ("PAYPAL", "PAYP", "PayPal")


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
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # ------------------------------------------------------------------
    # Saldo
    # ------------------------------------------------------------------

    def fetch_balance(self) -> Decimal:
        token = self._get_token()
        resp = httpx.get(
            f"{self._base_url()}/v1/reporting/balances",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        for bal in resp.json().get("balances", []):
            if bal.get("currency_code") == "EUR" and bal.get("type") == "AVAILABLE":
                return Decimal(bal["total_balance"]["value"])
        return Decimal("0.00")

    # ------------------------------------------------------------------
    # Movimientos (con paginación)
    # ------------------------------------------------------------------

    def fetch_transactions(self) -> list[RawTransaction]:
        token = self._get_token()
        start = _iso(date.today() - timedelta(days=90))
        end   = _iso(date.today())

        results: list[RawTransaction] = []
        page_num = 1

        while True:
            resp = httpx.get(
                f"{self._base_url()}/v1/reporting/transactions",
                params={
                    "start_date": start,
                    "end_date": end,
                    "fields": "all",
                    "page_size": 500,
                    "page": page_num,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("transaction_details", []):
                raw = _parse_item(item)
                if raw:
                    results.append(raw)

            total_pages = data.get("total_pages", 1)
            if page_num >= total_pages:
                break
            page_num += 1

        return results

    # ------------------------------------------------------------------
    # Post-sync: marcar passthrough en transacciones bancarias
    # ------------------------------------------------------------------

    def sync(self):
        imported = super().sync()
        mark_bank_passthroughs(self.db)
        return imported


# ------------------------------------------------------------------
# Función pública reutilizable: marcar passthroughs de PayPal en cuentas bancarias
# ------------------------------------------------------------------

def mark_bank_passthroughs(db) -> int:
    """
    Busca en todas las cuentas bancarias (no-PayPal) transacciones cuyo concepto
    contenga palabras clave de PayPal y las marca como excluir_de_gastos=True.

    Se llama tanto después del sync automático de PayPal como después de importar
    un extracto bancario CSV, para que los cargos "RECIBO PayPal Europe S.a.r.l."
    queden excluidos del cómputo de gastos (el gasto real consta en PayPal).

    Devuelve el número de transacciones marcadas en esta llamada.
    """
    from app.models.transaction import Transaction
    from app.models.account import Account
    from sqlalchemy import or_

    paypal_ids = [
        a.id for a in db.query(Account).filter(Account.proveedor == "PayPal").all()
    ]

    q = db.query(Transaction).filter(
        Transaction.origen == TransactionOrigin.bank,
        Transaction.excluir_de_gastos == False,
        or_(*[
            Transaction.concepto_original.ilike(f"%{kw}%")
            for kw in _PASSTHROUGH_KEYWORDS
        ]),
    )
    if paypal_ids:
        q = q.filter(Transaction.account_id.notin_(paypal_ids))

    found = q.all()
    for t in found:
        t.excluir_de_gastos = True
    if found:
        db.commit()
    return len(found)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _iso(d: date) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


def _parse_item(item: dict) -> RawTransaction | None:
    info   = item.get("transaction_info", {})
    amount = info.get("transaction_amount", {})
    if not amount:
        return None

    importe = Decimal(amount.get("value", "0"))
    if importe == 0:
        return None

    payer   = item.get("payer_info", {})
    comercio = (
        payer.get("payer_name", {}).get("alternate_full_name")
        or info.get("transaction_subject")
    )
    concepto = (
        info.get("transaction_note")
        or info.get("transaction_subject")
        or comercio
        or "PayPal"
    )

    fecha_raw = info.get("transaction_initiation_date", "")
    if not fecha_raw:
        return None

    return RawTransaction(
        fecha=date.fromisoformat(fecha_raw[:10]),
        importe=importe,
        concepto=concepto,
        comercio=comercio,
        origen=TransactionOrigin.paypal,
        paypal_transaction_id=info.get("transaction_id"),
    )
