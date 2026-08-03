import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Enum, Numeric, Boolean, Date, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TransactionOrigin(str, enum.Enum):
    bank = "bank"
    paypal = "paypal"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    importe: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    concepto_original: Mapped[str] = mapped_column(Text, nullable=False)
    comercio: Mapped[str | None] = mapped_column(String(200), nullable=True)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    subcategoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recurrente: Mapped[bool] = mapped_column(Boolean, default=False)
    origen: Mapped[TransactionOrigin] = mapped_column(Enum(TransactionOrigin), default=TransactionOrigin.bank)
    paypal_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    excluir_de_gastos: Mapped[bool] = mapped_column(Boolean, default=False)
    es_compartido: Mapped[bool] = mapped_column(Boolean, default=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="transactions")
    categoria: Mapped["Category | None"] = relationship(back_populates="transactions")
