import hashlib
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models.account import Account
from app.models.transaction import Transaction, TransactionOrigin, TransferEstado


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

    def sync(self) -> int:
        transactions = self.fetch_transactions()
        balance = self.fetch_balance()

        imported = 0
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
                origen=raw.origen,
                paypal_transaction_id=raw.paypal_transaction_id,
                hash=h,
            )
            self.db.add(t)
            imported += 1

        self.account.saldo_actual = balance
        self.account.ultima_sync = datetime.utcnow()
        self.db.commit()

        self._deduplicate_internal_transfers()
        return imported

    # ------------------------------------------------------------------
    # Deduplicación de transferencias internas
    # ------------------------------------------------------------------

    def _deduplicate_internal_transfers(self):
        """
        Empareja transacciones entre cuentas propias para evitar que una
        transferencia interna se cuente como gasto e ingreso a la vez.

        Criterios de emparejamiento:
          1. Primario: el concepto contiene el IBAN o alias de otra cuenta propia.
          2. Secundario: mismo importe absoluto, sentidos opuestos,
             fecha dentro de una ventana de 2 días hábiles.

        Resultado: ambas patas reciben categoria='Transferencias internas',
        excluir_de_gastos=True y transfer_estado='completo'.
        Si solo se encuentra una pata, queda en transfer_estado='pendiente'.
        """
        from app.models.category import Category

        # Obtener todas las cuentas propias activas
        own_accounts = (
            self.db.query(Account)
            .filter(Account.activa == True)
            .all()
        )
        own_ids = {a.id for a in own_accounts}
        own_ibans = {a.iban for a in own_accounts if a.iban}
        own_aliases = {a.alias for a in own_accounts}

        cat_interna = (
            self.db.query(Category)
            .filter(Category.nombre == "Transferencias internas")
            .first()
        )

        # Movimientos sin emparejar de la cuenta sincronizada
        unmatched = (
            self.db.query(Transaction)
            .filter(
                Transaction.account_id == self.account.id,
                Transaction.transfer_pair_id == None,
                Transaction.transfer_estado == None,
            )
            .all()
        )

        for tx in unmatched:
            concepto_upper = tx.concepto_original.upper()

            # Criterio 1: IBAN o alias de cuenta propia en el concepto
            is_internal_by_concept = any(
                (iban and iban.upper() in concepto_upper) or alias.upper() in concepto_upper
                for iban, alias in zip(
                    [a.iban for a in own_accounts],
                    [a.alias for a in own_accounts],
                )
            )

            if not is_internal_by_concept:
                # Criterio 2: buscar contraparte por importe y ventana de fechas
                window_start = tx.fecha - timedelta(days=2)
                window_end   = tx.fecha + timedelta(days=2)
                counterpart = (
                    self.db.query(Transaction)
                    .filter(
                        Transaction.account_id.in_(own_ids - {self.account.id}),
                        Transaction.importe == -tx.importe,
                        Transaction.fecha >= window_start,
                        Transaction.fecha <= window_end,
                        Transaction.transfer_pair_id == None,
                        Transaction.transfer_estado == None,
                    )
                    .first()
                )
            else:
                # Buscar contraparte en otras cuentas propias
                window_start = tx.fecha - timedelta(days=2)
                window_end   = tx.fecha + timedelta(days=2)
                counterpart = (
                    self.db.query(Transaction)
                    .filter(
                        Transaction.account_id.in_(own_ids - {self.account.id}),
                        Transaction.importe == -tx.importe,
                        Transaction.fecha >= window_start,
                        Transaction.fecha <= window_end,
                        Transaction.transfer_pair_id == None,
                    )
                    .first()
                )

            if counterpart:
                _mark_pair(tx, counterpart, cat_interna)
            elif is_internal_by_concept:
                # La contraparte aún no está sincronizada
                _mark_pending(tx, cat_interna)

        self.db.commit()

    def _hash(self, raw: RawTransaction) -> str:
        key = f"{self.account.id}|{raw.fecha}|{raw.importe}|{raw.concepto}"
        return hashlib.sha256(key.encode()).hexdigest()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _mark_pair(tx: Transaction, counterpart: Transaction, categoria):
    for t in (tx, counterpart):
        t.excluir_de_gastos = True
        t.transfer_estado = TransferEstado.completo
        if categoria:
            t.categoria_id = categoria.id
    # El ID más bajo apunta al más alto para evitar ciclo de FK
    lo, hi = (tx, counterpart) if tx.id < counterpart.id else (counterpart, tx)
    lo.transfer_pair_id = hi.id


def _mark_pending(tx: Transaction, categoria):
    tx.transfer_estado = TransferEstado.pendiente
    tx.excluir_de_gastos = False  # no excluir hasta confirmar el par
    if categoria:
        tx.categoria_id = categoria.id
