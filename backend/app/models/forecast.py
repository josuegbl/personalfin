from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ForecastPlan(Base):
    """Planned budget for a given month (revenues + variable category budgets)."""

    __tablename__ = "forecast_plans"
    __table_args__ = (UniqueConstraint("anio", "mes", name="uq_forecast_anio_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    anio: Mapped[int] = mapped_column(nullable=False)
    mes: Mapped[int] = mapped_column(nullable=False)
    # Legacy fields — kept for DB compatibility; income now comes from RecurringIncome
    ingresos_persona_a: Mapped[Decimal] = mapped_column("ingresos_josue", Numeric(10, 2), nullable=False, default=Decimal("0"))
    ingresos_persona_b: Mapped[Decimal] = mapped_column("ingresos_adi", Numeric(10, 2), nullable=False, default=Decimal("0"))
    ingresos_extra: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    # Personal budget allocations (planned share of income that stays in personal accounts)
    cuenta_personal_a: Mapped[Decimal] = mapped_column("cuenta_personal_josue", Numeric(10, 2), nullable=False, default=Decimal("0"))
    cuenta_personal_b: Mapped[Decimal] = mapped_column("cuenta_personal_adi", Numeric(10, 2), nullable=False, default=Decimal("0"))
    # User-editable planned income (gross nóminas). None = use computed from prev-month transactions.
    ingresos_planificados: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True, default=None)
    ingresos_planificados_a: Mapped[Optional[Decimal]] = mapped_column("ingresos_planificados_josue", Numeric(10, 2), nullable=True, default=None)
    ingresos_planificados_b: Mapped[Optional[Decimal]] = mapped_column("ingresos_planificados_adi", Numeric(10, 2), nullable=True, default=None)
    guardado: Mapped[bool] = mapped_column(nullable=False, default=False)

    budgets: Mapped[list["ForecastCategoryBudget"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class ForecastCategoryBudget(Base):
    """Planned spending for a single category within a ForecastPlan."""

    __tablename__ = "forecast_category_budgets"
    __table_args__ = (
        UniqueConstraint(
            "forecast_id",
            "categoria_id",
            name="uq_forecast_budget_categoria",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    forecast_id: Mapped[int] = mapped_column(ForeignKey("forecast_plans.id", ondelete="CASCADE"), nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", name="fk_forecast_category_budgets_categoria_id"),
        nullable=True,
    )
    importe_planificado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    plan: Mapped["ForecastPlan"] = relationship(back_populates="budgets")
    categoria: Mapped["Category | None"] = relationship("Category")
