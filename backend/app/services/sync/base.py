import hashlib
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.transaction import Transaction, TransactionOrigin


@dataclass
class RawTransaction:
    fecha: date
    importe: Decimal
    concepto: str
    comercio: str | None = None
    origen: TransactionOrigin = TransactionOrigin.bank
    paypal_transaction_id: str | None = None


class SourceAdapter(ABC):
    def __init__(self, account: Account, db: Session):
        self.account = account
        self.db = db

    @abstractmethod
    def fetch_transactions(self) -> list[RawTransaction]:
        """Descarga los movimientos de la fuente."""
        ...

    @abstractmethod
    def fetch_balance(self) -> Decimal:
        """Devuelve el saldo actual de la cuenta."""
        ...

    def sync(self):
        transactions = self.fetch_transactions()
        balance = self.fetch_balance()

        imported = 0
        for raw in transactions:
            h = self._hash(raw)
            exists = self.db.query(Transaction).filter(Transaction.hash == h).first()
            if exists:
                continue

            t = Transaction(
                account_id=self.account.id,
                fecha=raw.fecha,
                importe=raw.importe,
                concepto_original=raw.concepto,
                comercio=raw.comercio,
                origen=raw.origen,
                paypal_transaction_id=raw.paypal_transaction_id,
                hash=h,
            )
            self.db.add(t)
            imported += 1

        self.account.saldo_actual = balance
        self.account.ultima_sync = datetime.utcnow()
        self.db.commit()
        return imported

    def _hash(self, raw: RawTransaction) -> str:
        key = f"{self.account.id}|{raw.fecha}|{raw.importe}|{raw.concepto}"
        return hashlib.sha256(key.encode()).hexdigest()
