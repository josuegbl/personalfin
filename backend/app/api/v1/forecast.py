from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, false, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.category_catalog import CATEGORY_CODE_SIN_CATEGORIA
from app.core.date_limits import is_before_min_month
from app.core.forecast_catalog import FIXED_CATEGORY_NAMES, normalize_fixed_category_name
from app.models.category import Category
from app.models.forecast import ForecastCategoryBudget, ForecastPlan
from app.models.monthly_balance import MonthlyBalanceCategoryPlan, MonthlyBalancePlan
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
    """Return the two account incomes and personal allocations.

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
        Tuple of (account A income, account B income, account A personal, account B personal).
    """
    if plan.guardado:
        account_a_income = float(plan.ingresos_planificados_a) if plan.ingresos_planificados_a is not None else None
        account_b_income = float(plan.ingresos_planificados_b) if plan.ingresos_planificados_b is not None else None
        account_a_personal = float(plan.cuenta_personal_a)
        account_b_personal = float(plan.cuenta_personal_b)
    else:
        account_a_income = None
        account_b_income = None
        account_a_personal = None
        account_b_personal = None

    if any(v is None for v in [account_a_income, account_b_income, account_a_personal, account_b_personal]):
        prev = _last_saved_plan(year, month, db)
        if prev:
            if account_a_income is None and prev.ingresos_planificados_a is not None:
                account_a_income = float(prev.ingresos_planificados_a)
            if account_b_income is None and prev.ingresos_planificados_b is not None:
                account_b_income = float(prev.ingresos_planificados_b)
            if account_a_personal is None:
                account_a_personal = float(prev.cuenta_personal_a)
            if account_b_personal is None:
                account_b_personal = float(prev.cuenta_personal_b)

    if account_a_income is None or account_b_income is None:
        ri = db.query(RecurringIncome).filter(RecurringIncome.activa == True).all()  # noqa: E712
        if account_a_income is None:
            account_a_income = sum(
                float(r.importe) for r in ri
                if r.propietario and "cuenta_a" in r.propietario.lower()
            ) or 0.0
        if account_b_income is None:
            account_b_income = sum(
                float(r.importe) for r in ri
                if r.propietario and "cuenta_b" in r.propietario.lower()
            ) or 0.0

    return account_a_income or 0.0, account_b_income or 0.0, account_a_personal or 0.0, account_b_personal or 0.0


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
    balance_snapshot = (
        db.query(MonthlyBalancePlan)
        .options(selectinload(MonthlyBalancePlan.categorias))
        .filter(MonthlyBalancePlan.anio == year, MonthlyBalancePlan.mes == month)
        .first()
    )
    balance_cerrado = balance_snapshot is not None

    account_a_income, account_b_income, account_a_personal, account_b_personal = _effective_plan_values(plan, year, month, db)
    if balance_snapshot is not None:
        account_a_income = float(balance_snapshot.ingresos_planificados_josue)
        account_b_income = float(balance_snapshot.ingresos_planificados_adi)
        account_a_personal = float(balance_snapshot.cuenta_personal_josue)
        account_b_personal = float(balance_snapshot.cuenta_personal_adi)

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
        or_(~is_nomina, Transaction.categoria_id == None),  # noqa: E711
        or_(Category.id.is_(None), Category.incluida_en_analisis == True),  # noqa: E712
    ).one()
    ingresos_otros = float(otros_row[0])
    ingresos_reales = ingresos_nomina + ingresos_otros

    # --- Gastos fijos ---
    gastos_fijos = []
    fixed_by_category_id: dict[int, list[ForecastCategoryItem]] = defaultdict(list)
    grouped_fixed: dict[str, list[ForecastCategoryItem]] = defaultdict(list)
    for fixed_name in FIXED_CATEGORY_NAMES:
        grouped_fixed[fixed_name] = []

    if balance_snapshot is not None:
        for line in balance_snapshot.categorias:
            if line.tipo != "gasto_fijo":
                continue
            category = line.categoria
            parent_name = (
                category.parent.nombre
                if category is not None and category.parent is not None
                else category.nombre if category is not None else "Otros"
            )
            parent_name = normalize_fixed_category_name(parent_name)
            fixed_item = ForecastCategoryItem(
                categoria=parent_name,
                categoria_id=line.categoria_id,
                nombre=line.nombre,
                importe_planificado=float(line.importe_planificado),
                importe_real=0.0,
            )
            gastos_fijos.append(fixed_item)
            if line.categoria_id is not None:
                fixed_by_category_id[line.categoria_id].append(fixed_item)
            grouped_fixed[parent_name].append(fixed_item)
    else:
        all_recurring = (
            db.query(RecurringExpense)
            .options(
                selectinload(RecurringExpense.tiers),
                selectinload(RecurringExpense.subcategoria).selectinload(Category.parent),
            )
            .filter(
                or_(RecurringExpense.vigente_desde.is_(None), RecurringExpense.vigente_desde <= last_day),
                or_(RecurringExpense.vigente_hasta.is_(None), RecurringExpense.vigente_hasta >= first_day),
            )
            .all()
        )
        for expense in all_recurring:
            tier = _tier_for_month(expense, month)
            parent_name = None
            if expense.subcategoria and expense.subcategoria.parent:
                parent_name = expense.subcategoria.parent.nombre
            elif expense.categoria:
                parent_name = expense.categoria
            else:
                parent_name = "Otros"
            parent_name = normalize_fixed_category_name(parent_name)

            fixed_item = ForecastCategoryItem(
                id=expense.id,
                categoria=parent_name,
                categoria_id=expense.subcategoria_id,
                nombre=expense.concepto,
                importe_planificado=float(tier.importe) if tier else 0.0,
                importe_real=0.0,
                meses=tier.meses if tier else None,
                tiers=[
                    FixedExpenseTier(importe=float(item.importe), meses=item.meses)
                    for item in expense.tiers
                ],
            )
            gastos_fijos.append(fixed_item)
            if expense.subcategoria_id is not None:
                fixed_by_category_id[expense.subcategoria_id].append(fixed_item)
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
            Transaction.categoria_id.label("categoria_id"),
            Category.nombre.label("cat_nombre"),
            func.sum(Transaction.importe).label("total"),
        )
        .outerjoin(Category, Transaction.categoria_id == Category.id)
        .filter(and_(base_filter, Transaction.importe < 0))
        .group_by(Transaction.categoria_id, Category.nombre)
        .order_by(func.sum(Transaction.importe))
        .all()
    )

    real_by_category: dict[str, float] = {}
    real_category_ids: dict[str, int | None] = {}
    snapshot_budget_map: dict[str, float] | None = None
    budget_category_ids: dict[str, int] = {}
    if balance_snapshot is not None:
        snapshot_budget_map = {}
        for line in balance_snapshot.categorias:
            if line.tipo != "gasto_variable" or line.categoria is None:
                continue
            category_name = normalize_fixed_category_name(line.categoria.nombre)
            snapshot_budget_map[category_name] = float(line.importe_planificado)
            if line.categoria_id is not None:
                budget_category_ids[category_name] = line.categoria_id
    total_gastos_reales = 0.0
    for row in expense_rows:
        amount = float(abs(Decimal(str(row.total))))
        total_gastos_reales += amount
        matching_fixed = fixed_by_category_id.get(row.categoria_id, [])
        if len(matching_fixed) == 1:
            matching_fixed[0].importe_real += amount
        else:
            category_name = row.cat_nombre or "Sin categoría"
            real_by_category[category_name] = real_by_category.get(category_name, 0.0) + amount
            real_category_ids[category_name] = row.categoria_id

    gastos_reales_por_categoria = [
        ForecastCategoryItem(
            categoria_id=real_category_ids.get(nombre),
            nombre=nombre,
            importe_planificado=0.0,
            importe_real=importe,
        )
        for nombre, importe in real_by_category.items()
    ]

    budget_map: dict[str, float] = snapshot_budget_map if snapshot_budget_map is not None else {}
    if snapshot_budget_map is None:
        for budget in plan.budgets:
            if budget.categoria is None:
                continue
            category_name = normalize_fixed_category_name(budget.categoria.nombre)
            budget_map[category_name] = float(budget.importe_planificado)
            if budget.categoria_id is not None:
                budget_category_ids[category_name] = budget.categoria_id
    variable_order = sorted(budget_map.keys(), key=str.lower)
    gastos_variables = [
        ForecastCategoryItem(
            categoria=name,
            categoria_id=budget_category_ids.get(name),
            nombre=name,
            importe_planificado=budget_map.get(name, 0.0),
            importe_real=real_by_category.get(name, 0.0),
        )
        for name in variable_order
    ]

    # --- Totals ---
    total_cuentas_personales_plan = account_a_personal + account_b_personal
    total_gastos_fijos_plan = sum(item.importe_planificado for item in gastos_fijos)
    total_gastos_variables_plan = sum(item.importe_planificado for item in gastos_variables)
    ahorro_estimado = (
        account_a_income
        + account_b_income
        - total_cuentas_personales_plan
        - total_gastos_fijos_plan
        - total_gastos_variables_plan
    )
    total_gastos_reales += total_cuentas_personales_plan

    return ForecastResponse(
        anio=year,
        mes=month,
        es_ejecucion=es_ejecucion,
        balance_cerrado=balance_cerrado,
        plan_guardado=plan.guardado,
        cuenta_personal_a=account_a_personal,
        cuenta_personal_b=account_b_personal,
        ingresos_planificados=(
            float(balance_snapshot.ingresos_planificados)
            if balance_snapshot is not None
            else float(plan.ingresos_planificados) if plan.ingresos_planificados is not None else None
        ),
        ingresos_persona_a=account_a_income,
        ingresos_persona_b=account_b_income,
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


@router.post("/{year}/{month}/close", response_model=ForecastResponse)
def close_forecast_month(year: int, month: int, db: Session = Depends(get_db)) -> ForecastResponse:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=400, detail="month must be between 1 and 12")
    if is_before_min_month(year, month):
        raise HTTPException(status_code=400, detail="month is before the supported date range")

    if db.query(MonthlyBalancePlan.id).filter_by(anio=year, mes=month).first() is not None:
        raise HTTPException(status_code=409, detail="El balance del mes ya está cerrado")

    month_end = date(year, month, monthrange(year, month)[1])
    if month_end >= date.today():
        raise HTTPException(status_code=400, detail="Solo se pueden cerrar meses que ya han terminado")

    plan = db.query(ForecastPlan).filter_by(anio=year, mes=month).first()
    if plan is None or not plan.guardado:
        raise HTTPException(status_code=409, detail="Guarda la planificación antes de cerrar el mes")

    response = _build_response(plan, month, year, db)
    category_by_code = (
        db.query(Category)
        .filter(Category.codigo_sistema == CATEGORY_CODE_SIN_CATEGORIA)
        .first()
    )

    fixed_lines: list[MonthlyBalanceCategoryPlan] = []
    fixed_keys: set[tuple[int, str]] = set()
    for expense in response.gastos_fijos:
        planned = Decimal(str(expense.importe_planificado))
        actual_at_close = Decimal(str(expense.importe_real))
        if planned == 0 and actual_at_close == 0:
            continue
        if expense.categoria_id is None:
            raise HTTPException(
                status_code=409,
                detail=f"El gasto fijo {expense.nombre} no tiene categoría enlazada",
            )
        key = (expense.categoria_id, expense.nombre)
        if key in fixed_keys:
            raise HTTPException(
                status_code=409,
                detail=f"Hay gastos fijos duplicados para {expense.nombre}",
            )
        fixed_keys.add(key)
        fixed_lines.append(MonthlyBalanceCategoryPlan(
            tipo="gasto_fijo",
            categoria_id=expense.categoria_id,
            nombre=expense.nombre,
            importe_planificado=planned,
        ))

    variable_plan: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for category in response.gastos_variables:
        if category.categoria_id is None:
            raise HTTPException(
                status_code=409,
                detail=f"La categoría variable {category.nombre} no tiene ID",
            )
        variable_plan[category.categoria_id] += Decimal(str(category.importe_planificado))

    variable_ids = set(variable_plan)
    for category in response.gastos_reales_por_categoria:
        category_id = category.categoria_id
        if category_id is None:
            if category_by_code is None:
                raise HTTPException(status_code=409, detail="No existe la categoría Sin categoría")
            category_id = category_by_code.id
        variable_ids.add(category_id)

    variable_lines: list[MonthlyBalanceCategoryPlan] = []
    for category_id in variable_ids:
        planned = variable_plan.get(category_id, Decimal("0"))
        actual_at_close = sum(
            Decimal(str(item.importe_real))
            for item in response.gastos_reales_por_categoria
            if item.categoria_id == category_id
            or (item.categoria_id is None and category_by_code is not None and category_id == category_by_code.id)
        )
        if planned == 0 and actual_at_close == 0:
            continue
        variable_lines.append(MonthlyBalanceCategoryPlan(
            tipo="gasto_variable",
            categoria_id=category_id,
            nombre=None,
            importe_planificado=planned,
        ))

    snapshot = MonthlyBalancePlan(
        anio=year,
        mes=month,
        ingresos_planificados=Decimal(str(
            response.ingresos_planificados
            if response.ingresos_planificados is not None
            else response.ingresos_persona_a + response.ingresos_persona_b
        )),
        ingresos_planificados_josue=Decimal(str(response.ingresos_persona_a)),
        ingresos_planificados_adi=Decimal(str(response.ingresos_persona_b)),
        cuenta_personal_josue=Decimal(str(response.cuenta_personal_a)),
        cuenta_personal_adi=Decimal(str(response.cuenta_personal_b)),
        categorias=[*fixed_lines, *variable_lines],
    )
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="El mes ya se ha cerrado") from error

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

    if db.query(MonthlyBalancePlan.id).filter_by(anio=year, mes=month).first() is not None:
        raise HTTPException(status_code=409, detail="El balance del mes ya está cerrado")

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

    plan.cuenta_personal_a = Decimal(str(body.cuenta_personal_a))
    plan.cuenta_personal_b = Decimal(str(body.cuenta_personal_b))
    plan.ingresos_planificados_a = Decimal(str(body.ingresos_persona_a))
    plan.ingresos_planificados_b = Decimal(str(body.ingresos_persona_b))
    plan.ingresos_planificados = Decimal(str(body.ingresos_persona_a + body.ingresos_persona_b))
    plan.guardado = True

    incoming_budget_map = {
        normalize_fixed_category_name(cat.nombre): Decimal(str(cat.importe_planificado))
        for cat in body.categorias
    }
    available_categories = db.query(Category).all()
    categories_by_name = {
        normalize_fixed_category_name(category.nombre): category
        for category in available_categories
    }
    missing_categories = incoming_budget_map.keys() - categories_by_name.keys()
    if missing_categories:
        missing_name = sorted(missing_categories)[0]
        raise HTTPException(
            status_code=400,
            detail=f"Categoría de presupuesto no encontrada: {missing_name}",
        )

    for budget in list(plan.budgets):
        db.delete(budget)
    db.flush()

    for category_name, amount in incoming_budget_map.items():
        db.add(ForecastCategoryBudget(
            plan=plan,
            categoria_id=categories_by_name[category_name].id,
            importe_planificado=amount,
        ))

    if body.propagar_campos:
        field_attributes = {
            "cuenta_personal_a": "cuenta_personal_a",
            "cuenta_personal_b": "cuenta_personal_b",
            "ingresos_persona_a": "ingresos_planificados_a",
            "ingresos_persona_b": "ingresos_planificados_b",
        }
        future_plans = (
            db.query(ForecastPlan)
            .filter(
                ForecastPlan.guardado == True,  # noqa: E712
                or_(
                    ForecastPlan.anio > year,
                    and_(ForecastPlan.anio == year, ForecastPlan.mes > month),
                ),
            )
            .all()
        )
        closed_future_months = {
            (snapshot.anio, snapshot.mes)
            for snapshot in db.query(MonthlyBalancePlan)
            .filter(
                or_(
                    MonthlyBalancePlan.anio > year,
                    and_(MonthlyBalancePlan.anio == year, MonthlyBalancePlan.mes > month),
                )
            )
            .all()
        }
        for future_plan in future_plans:
            if (future_plan.anio, future_plan.mes) in closed_future_months:
                continue
            income_fields_changed = False
            for field in body.propagar_campos:
                attribute = field_attributes[field]
                setattr(future_plan, attribute, getattr(plan, attribute))
                if field.startswith("ingresos_persona_"):
                    income_fields_changed = True
            if (
                income_fields_changed
                and future_plan.ingresos_planificados_a is not None
                and future_plan.ingresos_planificados_b is not None
            ):
                future_plan.ingresos_planificados = (
                    future_plan.ingresos_planificados_a
                    + future_plan.ingresos_planificados_b
                )

    db.commit()
    db.refresh(plan)

    return _build_response(plan, month, year, db)
