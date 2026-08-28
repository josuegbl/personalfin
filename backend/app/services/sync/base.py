import hashlib
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


@dataclass
class RawTransaction:
    fecha: date
    importe: Decimal
    concepto: str
    comercio: str | None = None


def _is_payroll(raw: RawTransaction) -> bool:
    text = f"{raw.concepto} {raw.comercio or ''}".upper()
    return raw.importe > 0 and ("NOMINA" in text or "NÓMINA" in text)


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

    def sync(self) -> int:
        transactions = self.fetch_transactions()
        balance = self.fetch_balance()
        return self._persist(transactions, balance)

    def _persist(self, transactions: list[RawTransaction], balance: Decimal) -> int:
        imported = 0
        uncategorized = (
            self.db.query(Category)
            .filter(Category.nombre == "Sin categoría")
            .first()
        )
        payroll = self.db.query(Category).filter(Category.nombre == "Nómina").first()
        for raw in transactions:
            h = self._hash(raw)
            if self.db.query(Transaction).filter(Transaction.hash == h).first():
                continue

            t = Transaction(
                account_id=self.account.id,
                fecha=raw.fecha,
                importe=raw.importe,
                concepto_original=raw.concepto,
                comercio=raw.comercio,
                categoria_id=(
                    payroll.id
                    if payroll and _is_payroll(raw)
                    else uncategorized.id if uncategorized else None
                ),
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


class CSVImportAdapter(SourceAdapter):
    """
    Adapter genérico para importar transacciones ya parseadas desde un CSV.
    Úsalo cuando el CSV ya ha sido parseado externamente y solo necesitas
    persistirlo evitando reimportar movimientos ya presentes.
    """

    def __init__(self, account, db, transactions: list[RawTransaction], balance: Decimal):
        super().__init__(account, db)
        self._transactions = transactions
        self._balance = balance

    def fetch_transactions(self) -> list[RawTransaction]:
        return self._transactions

    def fetch_balance(self) -> Decimal:
        return self._balance
