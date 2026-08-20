from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, false, func, or_
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.forecast_catalog import FIXED_CATEGORY_NAMES, normalize_fixed_category_name
from app.models.category import Category
from app.models.forecast import ForecastCategoryBudget, ForecastPlan
from app.models.recurring_expense import RecurringExpense
from app.models.recurring_income import RecurringIncome
from app.models.transaction import Transaction
from app.schemas.forecast import (
    FixedCategoryGroup,
    FixedExpenseTier,
    ForecastCategoryItem,
    ForecastPlanUpdate,
    ForecastResponse,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])

def _tier_for_month(expense: RecurringExpense, month: int):
    """Return the applicable tier for this month, or None if expense doesn't apply.

    Checks tiers with specific months first, then falls back to the catch-all tier
    (meses=None). Returns None when no tier matches.

    Args:
        expense: The recurring expense with its tiers loaded.
        month: The target month (1–12).

    Returns:
        The matching RecurringExpenseTier, or None.
    """
    for tier in expense.tiers:
        if tier.meses and month in tier.meses:
            return tier
    for tier in expense.tiers:
        if tier.meses is None:
            return tier
    return None


def _prev_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the month prior to the given one."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _nomina_condition(db: Session):
    """Build a SQLAlchemy OR condition that identifies salary transactions.

    Matches only transactions assigned to the Nómina category.

    Args:
        db: Database session.

    Returns:
        A SQLAlchemy OR clause for filtering salary transactions.
    """
    nomina_cat = db.query(Category).filter(Category.nombre == "Nómina").first()
    if nomina_cat:
        return Transaction.categoria_id == nomina_cat.id
    return false()


def _last_saved_plan(year: int, month: int, db: Session) -> "ForecastPlan | None":
    """Return the most recent ForecastPlan before this month that was explicitly saved.

    Args:
        year: Target year.
        month: Target month (1–12).
        db: Database session.

    Returns:
        The most recently saved ForecastPlan before the given month, or None.
    """
    return (
        db.query(ForecastPlan)
        .filter(
            ForecastPlan.guardado == True,  # noqa: E712
            or_(
                ForecastPlan.anio < year,
                and_(ForecastPlan.anio == year, ForecastPlan.mes < month),
            ),
        )
        .order_by(ForecastPlan.anio.desc(), ForecastPlan.mes.desc())
        .first()
    )


def _effective_plan_values(
    plan: ForecastPlan, year: int, month: int, db: Session
) -> tuple[float, float, float, float]:
    """Return (josue_income, adi_income, josue_personal, adi_personal) effective values.

    Priority:
      1. Current plan's explicitly saved values (if plan.guardado).
      2. Most recent previously saved plan's values.
      3. RecurringIncome amounts (for income) / 0 (for personal).

    Args:
        plan: Current month's ForecastPlan.
        year: Target year.
        month: Target month (1–12).
        db: Database session.

    Returns:
        Tuple of (josue_income, adi_income, josue_personal, adi_personal).
    """
    if plan.guardado:
        josue_inc = float(plan.ingresos_planificados_josue) if plan.ingresos_planificados_josue is not None else None
        adi_inc = float(plan.ingresos_planificados_adi) if plan.ingresos_planificados_adi is not None else None
        josue_per = float(plan.cuenta_personal_josue)
        adi_per = float(plan.cuenta_personal_adi)
    else:
        josue_inc = None
        adi_inc = None
        josue_per = None
        adi_per = None

    if any(v is None for v in [josue_inc, adi_inc, josue_per, adi_per]):
        prev = _last_saved_plan(year, month, db)
        if prev:
            if josue_inc is None and prev.ingresos_planificados_josue is not None:
                josue_inc = float(prev.ingresos_planificados_josue)
            if adi_inc is None and prev.ingresos_planificados_adi is not None:
                adi_inc = float(prev.ingresos_planificados_adi)
            if josue_per is None:
                josue_per = float(prev.cuenta_personal_josue)
            if adi_per is None:
                adi_per = float(prev.cuenta_personal_adi)

    if josue_inc is None or adi_inc is None:
        ri = db.query(RecurringIncome).filter(RecurringIncome.activa == True).all()  # noqa: E712
        if josue_inc is None:
            josue_inc = sum(
                float(r.importe) for r in ri
                if r.propietario and "josue" in r.propietario.lower()
            ) or 0.0
        if adi_inc is None:
            adi_inc = sum(
                float(r.importe) for r in ri
                if r.propietario and "adi" in r.propietario.lower()
            ) or 0.0

    return josue_inc or 0.0, adi_inc or 0.0, josue_per or 0.0, adi_per or 0.0


def _build_response(plan: ForecastPlan, month: int, year: int, db: Session) -> ForecastResponse:
    """Assemble a ForecastResponse by combining plan data with live transaction data.

    Income split:
      - Salary (nómina) transactions from month M-1, minus planned personal allocations,
        form the deferred income base for month M.
      - All other positive non-excluded transactions from month M (refunds, misc
        transfers, etc.) are counted as current-month income.

    Income and expense totals are determined by the sign of each transaction.
    Categories provide the breakdown, while category-specific inclusion rules
    remain reserved for a later phase.

    Args:
        plan: The ForecastPlan ORM object for this month.
        month: Target month (1–12).
        year: Target year.
        db: Database session.

    Returns:
        Full forecast + execution data for the month.
    """
    today = date.today()
    es_ejecucion = date(year, month, 1) < date(today.year, today.month, 1)

    josue_inc, adi_inc, josue_per, adi_per = _effective_plan_values(plan, year, month, db)

    is_nomina = _nomina_condition(db)

    # --- Salary income from PREVIOUS month ---
    prev_year, prev_month = _prev_month(year, month)
    prev_first = date(prev_year, prev_month, 1)
    prev_last = date(prev_year, prev_month, monthrange(prev_year, prev_month)[1])

    nomina_row = db.query(
        func.coalesce(func.sum(Transaction.importe), 0)
    ).outerjoin(Category, Transaction.categoria_id == Category.id).filter(
        Transaction.fecha >= prev_first,
        Transaction.fecha <= prev_last,
        Transaction.importe > 0,
        is_nomina,
        or_(Category.id.is_(None), Category.incluida_en_analisis == True),  # noqa: E712
    ).one()
    ingresos_nomina = float(nomina_row[0])

    # --- Other income from CURRENT month (non-salary) ---
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    otros_row = db.query(
        func.coalesce(func.sum(Transaction.importe), 0)
    ).outerjoin(Category, Transaction.categoria_id == Category.id).filter(
        Transaction.fecha >= first_day,
        Transaction.fecha <= last_day,
        Transaction.importe > 0,
        or_(~is_nomina, Transaction.categoria_id == None),
        or_(Category.id.is_(None), Category.incluida_en_analisis == True),  # noqa: E712
    ).one()
    ingresos_otros = float(otros_row[0])

    ingresos_reales = ingresos_nomina + ingresos_otros

    # --- Gastos fijos ---
    all_recurring = (
        db.query(RecurringExpense)
        .options(
            selectinload(RecurringExpense.tiers),
            selectinload(RecurringExpense.subcategoria).selectinload(Category.parent),
        )
        .all()
    )
    gastos_fijos = []
    grouped_fixed: dict[str, list[ForecastCategoryItem]] = defaultdict(list)
    for fixed_name in FIXED_CATEGORY_NAMES:
        grouped_fixed[fixed_name] = []

    for r in all_recurring:
        tier = _tier_for_month(r, month)
        parent_name = None
        if r.subcategoria and r.subcategoria.parent:
            parent_name = r.subcategoria.parent.nombre
        elif r.categoria:
            parent_name = r.categoria
        else:
            parent_name = "Otros"
        parent_name = normalize_fixed_category_name(parent_name)

        fixed_item = ForecastCategoryItem(
            id=r.id,
            categoria=parent_name,
            nombre=(r.subcategoria.nombre if r.subcategoria else r.concepto),
            importe_planificado=float(tier.importe) if tier else 0.0,
            importe_real=0.0,
            meses=tier.meses if tier else None,
            tiers=[
                FixedExpenseTier(importe=float(t.importe), meses=t.meses)
                for t in r.tiers
            ],
        )
        gastos_fijos.append(fixed_item)
        grouped_fixed[parent_name].append(fixed_item)

    for key, items in grouped_fixed.items():
        grouped_fixed[key] = sorted(items, key=lambda item: item.nombre.lower())

    # --- Gastos reales del mes actual ---
    base_filter = and_(
        Transaction.fecha >= first_day,
        Transaction.fecha <= last_day,
        or_(Category.id.is_(None), Category.incluida_en_analisis == True),  # noqa: E712
    )

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

    budget_map: dict[str, float] = {
        normalize_fixed_category_name(b.categoria_nombre): float(b.importe_planificado)
        for b in plan.budgets
    }
    variable_order = sorted(budget_map.keys(), key=str.lower)
    gastos_variables = [
        ForecastCategoryItem(
            categoria=name,
            nombre=name,
            importe_planificado=budget_map.get(name, 0.0),
            importe_real=real_by_category.get(name, 0.0),
        )
        for name in variable_order
    ]

    # --- Totals ---
    total_cuentas_personales_plan = josue_per + adi_per
    total_gastos_fijos_plan = sum(item.importe_planificado for item in gastos_fijos)
    total_gastos_variables_plan = sum(item.importe_planificado for item in gastos_variables)
    ahorro_estimado = (
        josue_inc
        + adi_inc
        - total_cuentas_personales_plan
        - total_gastos_fijos_plan
        - total_gastos_variables_plan
    )
    total_gastos_reales += total_cuentas_personales_plan

    return ForecastResponse(
        anio=year,
        mes=month,
        es_ejecucion=es_ejecucion,
        cuenta_personal_josue=josue_per,
        cuenta_personal_adi=adi_per,
        ingresos_planificados=float(plan.ingresos_planificados) if plan.ingresos_planificados is not None else None,
        ingresos_josue=josue_inc,
        ingresos_adi=adi_inc,
        ingresos_nomina=ingresos_nomina,
        ingresos_otros=ingresos_otros,
        ingresos_reales=ingresos_reales,
        gastos_fijos=gastos_fijos,
        gastos_fijos_por_categoria=[
            FixedCategoryGroup(categoria=name, subcategorias=grouped_fixed[name])
            for name in [*FIXED_CATEGORY_NAMES, *sorted(
                [k for k in grouped_fixed.keys() if k not in FIXED_CATEGORY_NAMES],
                key=str.lower,
            )]
        ],
        gastos_variables=gastos_variables,
        gastos_reales_por_categoria=gastos_reales_por_categoria,
        total_cuentas_personales_plan=total_cuentas_personales_plan,
        total_gastos_fijos_plan=total_gastos_fijos_plan,
        total_gastos_variables_plan=total_gastos_variables_plan,
        ahorro_estimado=ahorro_estimado,
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
    """Create or update the forecast plan for the current or a future month.

    Past months (execution) are read-only and cannot be modified via this endpoint.

    Args:
        year: The target year.
        month: The target month (1–12).
        body: New plan data (personal budgets + variable category budgets).
        db: Database session.

    Returns:
        Updated forecast data.

    Raises:
        HTTPException: If month is out of range or the month is in the past.
    """
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be between 1 and 12")

    today = date.today()
    if date(year, month, 1) < date(today.year, today.month, 1):
        raise HTTPException(
            status_code=400,
            detail="Los datos de ejecución de meses pasados no se pueden modificar",
        )

    plan = db.query(ForecastPlan).filter_by(anio=year, mes=month).first()
    if plan is None:
        plan = ForecastPlan(anio=year, mes=month)
        db.add(plan)

    plan.cuenta_personal_josue = Decimal(str(body.cuenta_personal_josue))
    plan.cuenta_personal_adi = Decimal(str(body.cuenta_personal_adi))
    plan.ingresos_planificados_josue = Decimal(str(body.ingresos_josue))
    plan.ingresos_planificados_adi = Decimal(str(body.ingresos_adi))
    plan.ingresos_planificados = Decimal(str(body.ingresos_josue + body.ingresos_adi))
    plan.guardado = True

    for budget in list(plan.budgets):
        db.delete(budget)
    db.flush()

    incoming_budget_map = {
        normalize_fixed_category_name(cat.nombre): Decimal(str(cat.importe_planificado))
        for cat in body.categorias
    }

    for category_name, amount in incoming_budget_map.items():
        db.add(ForecastCategoryBudget(
            plan=plan,
            categoria_nombre=category_name,
            importe_planificado=amount,
        ))

    db.commit()
    db.refresh(plan)

    return _build_response(plan, month, year, db)
