import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Enum, Numeric, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AccountType(str, enum.Enum):
    bank = "bank"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tipo: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    proveedor: Mapped[str] = mapped_column(String(50), nullable=False)  # BBVA, Eurocaja Rural
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    saldo_actual: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    moneda: Mapped[str] = mapped_column(String(3), default="EUR")
    propietario: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    visible_dashboard: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ultima_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")
