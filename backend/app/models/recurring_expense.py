from decimal import Decimal
from sqlalchemy import String, Numeric, ForeignKey, ARRAY, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RecurringExpense(Base):
    __tablename__ = "recurring_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    importe: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    # 'fijo' = todos los meses, 'estacional' = solo ciertos meses, 'variable' = estimado
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, default="fijo")
    # Meses en que aplica (1-12); NULL = todos los meses
    meses: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)
    dia_cobro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)

    account: Mapped["Account | None"] = relationship()
    tiers: Mapped[list["RecurringExpenseTier"]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
        order_by="RecurringExpenseTier.id",
    )


class RecurringExpenseTier(Base):
    __tablename__ = "recurring_expense_tiers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_expenses.id", ondelete="CASCADE"), nullable=False
    )
    importe: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    meses: Mapped[list[int] | None] = mapped_column(ARRAY(Integer), nullable=True)

    expense: Mapped["RecurringExpense"] = relationship(back_populates="tiers")
