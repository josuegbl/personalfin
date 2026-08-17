from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.category import Category
from app.models.forecast import ForecastCategoryBudget, ForecastPlan
from app.models.recurring_expense import RecurringExpense
from app.models.transaction import Transaction
from app.schemas.forecast import (
    ForecastCategoryItem,
    ForecastPlanUpdate,
    ForecastResponse,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _build_response(plan: ForecastPlan, month: int, year: int, db: Session) -> ForecastResponse:
    """Assemble a ForecastResponse by combining plan data with live transaction data."""
    all_recurring = db.query(RecurringExpense).all()
    recurring = [r for r in all_recurring if r.meses is None or month in r.meses]
    gastos_fijos = [
        ForecastCategoryItem(nombre=r.concepto, importe_planificado=float(r.importe), importe_real=0.0)
        for r in recurring
    ]

    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    base_filter = and_(
        Transaction.fecha >= first_day,
        Transaction.fecha <= last_day,
        Transaction.excluir_de_gastos == False,  # noqa: E712
    )

    income_row = db.query(
        func.coalesce(func.sum(Transaction.importe).filter(Transaction.importe > 0), 0)
    ).filter(base_filter).one()
    ingresos_reales = float(income_row[0])

    expense_rows = (
        db.query(
            Category.nombre.label("cat_nombre"),
            func.sum(Transaction.importe).label("total"),
        )
        .outerjoin(Category, Transaction.categoria_id == Category.id)
        .filter(and_(base_filter, Transaction.importe < 0))
        .group_by(Category.nombre)
        .order_by(func.sum(Transaction.importe))
        .all()
    )

    real_by_category: dict[str, float] = {
        (row.cat_nombre or "Sin categoría"): float(abs(Decimal(str(row.total))))
        for row in expense_rows
    }
    total_gastos_reales = sum(real_by_category.values())

    gastos_reales_por_categoria = [
        ForecastCategoryItem(nombre=nombre, importe_planificado=0.0, importe_real=importe)
        for nombre, importe in real_by_category.items()
    ]

    gastos_variables = [
        ForecastCategoryItem(
            nombre=b.categoria_nombre,
            importe_planificado=float(b.importe_planificado),
            importe_real=real_by_category.get(b.categoria_nombre, 0.0),
        )
        for b in plan.budgets
    ]

    total_ingresos_plan = float(plan.ingresos_josue + plan.ingresos_adi + plan.ingresos_extra)
    total_gastos_fijos_plan = sum(item.importe_planificado for item in gastos_fijos)
    total_gastos_variables_plan = sum(item.importe_planificado for item in gastos_variables)
    ahorro_estimado = total_ingresos_plan - total_gastos_fijos_plan - total_gastos_variables_plan

    return ForecastResponse(
        anio=year,
        mes=month,
        ingresos_josue=float(plan.ingresos_josue),
        ingresos_adi=float(plan.ingresos_adi),
        ingresos_extra=float(plan.ingresos_extra),
        gastos_fijos=gastos_fijos,
        gastos_variables=gastos_variables,
        gastos_reales_por_categoria=gastos_reales_por_categoria,
        total_ingresos_plan=total_ingresos_plan,
        total_gastos_fijos_plan=total_gastos_fijos_plan,
        total_gastos_variables_plan=total_gastos_variables_plan,
        ahorro_estimado=ahorro_estimado,
        ingresos_reales=ingresos_reales,
        total_gastos_reales=total_gastos_reales,
        ahorro_real=ingresos_reales - total_gastos_reales,
    )


@router.get("/{year}/{month}", response_model=ForecastResponse)
def get_forecast(year: int, month: int, db: Session = Depends(get_db)) -> ForecastResponse:
    """Return the forecast plan and real execution data for a given month.

    Args:
        year: The target year.
        month: The target month (1–12).
        db: Database session.

    Returns:
        Combined plan + execution data for the month.

    Raises:
        HTTPException: If month is out of range.
    """
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be between 1 and 12")

    plan = db.query(ForecastPlan).filter_by(anio=year, mes=month).first()
    if plan is None:
        plan = ForecastPlan(anio=year, mes=month)
        db.add(plan)
        db.commit()
        db.refresh(plan)

    return _build_response(plan, month, year, db)


@router.put("/{year}/{month}", response_model=ForecastResponse)
def upsert_forecast(
    year: int,
    month: int,
    body: ForecastPlanUpdate,
    db: Session = Depends(get_db),
) -> ForecastResponse:
    """Create or update the forecast plan for a given month.

    Args:
        year: The target year.
        month: The target month (1–12).
        body: New plan data (revenues + variable category budgets).
        db: Database session.

    Returns:
        Updated forecast data.

    Raises:
        HTTPException: If month is out of range.
    """
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be between 1 and 12")

    plan = db.query(ForecastPlan).filter_by(anio=year, mes=month).first()
    if plan is None:
        plan = ForecastPlan(anio=year, mes=month)
        db.add(plan)

    plan.ingresos_josue = Decimal(str(body.ingresos_josue))
    plan.ingresos_adi = Decimal(str(body.ingresos_adi))
    plan.ingresos_extra = Decimal(str(body.ingresos_extra))

    for budget in list(plan.budgets):
        db.delete(budget)
    db.flush()

    for cat in body.categorias:
        db.add(ForecastCategoryBudget(
            plan=plan,
            categoria_nombre=cat.nombre,
            importe_planificado=Decimal(str(cat.importe_planificado)),
        ))

    db.commit()
    db.refresh(plan)

    return _build_response(plan, month, year, db)
