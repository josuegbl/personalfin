from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecurringIncome(Base):
    """Expected recurring income source (salary, pension, etc.)."""

    __tablename__ = "recurring_incomes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    importe: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    propietario: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    orden: Mapped[int] = mapped_column(nullable=False, default=0)
