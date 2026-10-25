from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MonthlyBalancePlan(Base):
    __tablename__ = "monthly_balance_plans"
    __table_args__ = (UniqueConstraint("anio", "mes", name="uq_monthly_balance_anio_mes"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    anio: Mapped[int] = mapped_column(nullable=False)
    mes: Mapped[int] = mapped_column(nullable=False)
    ingresos_planificados: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0"
    )
    ingresos_planificados_josue: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0"
    )
    ingresos_planificados_adi: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0"
    )
    cuenta_personal_josue: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0"
    )
    cuenta_personal_adi: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, server_default="0"
    )
    gastos_corregidos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ingresos_corregidos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    categorias: Mapped[list["MonthlyBalanceCategoryPlan"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class MonthlyBalanceCategoryPlan(Base):
    __tablename__ = "monthly_balance_category_plans"
    __table_args__ = (
        UniqueConstraint(
            "balance_plan_id",
            "tipo",
            "nombre",
            name="uq_monthly_balance_category_tipo_nombre",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    balance_plan_id: Mapped[int] = mapped_column(
        ForeignKey("monthly_balance_plans.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    categoria_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    importe_planificado: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", name="fk_monthly_balance_category_plans_categoria_id"),
        nullable=True,
    )

    plan: Mapped[MonthlyBalancePlan] = relationship(back_populates="categorias")
    categoria: Mapped["Category | None"] = relationship("Category")
