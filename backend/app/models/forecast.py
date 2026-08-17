from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ForecastPlan(Base):
    """Planned budget for a given month (revenues + variable category budgets)."""

    __tablename__ = "forecast_plans"
    __table_args__ = (UniqueConstraint("anio", "mes", name="uq_forecast_anio_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    anio: Mapped[int] = mapped_column(nullable=False)
    mes: Mapped[int] = mapped_column(nullable=False)
    ingresos_josue: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    ingresos_adi: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    ingresos_extra: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))

    budgets: Mapped[list["ForecastCategoryBudget"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class ForecastCategoryBudget(Base):
    """Planned spending for a single category within a ForecastPlan."""

    __tablename__ = "forecast_category_budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    forecast_id: Mapped[int] = mapped_column(ForeignKey("forecast_plans.id", ondelete="CASCADE"), nullable=False)
    categoria_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    importe_planificado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    plan: Mapped["ForecastPlan"] = relationship(back_populates="budgets")
