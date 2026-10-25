from calendar import monthrange
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from app.core.database import get_db
from app.core.date_limits import is_before_min_month
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.dashboard import DashboardData, AccountBalance, MonthlySummary, CategoryExpense
from app.schemas.account import AccountOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _monthly_summary(db: Session, year: int, month: int) -> MonthlySummary:
    q = db.query(
        func.coalesce(
            func.sum(Transaction.importe).filter(
                Transaction.importe > 0
            ),
            0,
        ),
        func.coalesce(
            func.sum(Transaction.importe).filter(
                Transaction.importe < 0
            ),
            0,
        ),
        func.count(Transaction.id),
    ).outerjoin(Category, Transaction.categoria_id == Category.id).filter(
        and_(
            extract("year", Transaction.fecha) == year,
            extract("month", Transaction.fecha) == month,
            or_(Category.id.is_(None), Category.incluida_en_analisis == True),  # noqa: E712
        )
    ).one()

    ingresos = Decimal(str(q[0]))
    gastos = abs(Decimal(str(q[1])))
    return MonthlySummary(
        anio=year,
        mes=month,
        ingresos=ingresos,
        gastos=gastos,
        ahorro=ingresos - gastos,
        num_transacciones=q[2],
    )


def _category_expenses(db: Session, start_date: date, end_date: date) -> list[CategoryExpense]:
    rows = (
        db.query(
            Transaction.categoria_id,
            Category.nombre,
            Category.color,
            func.sum(Transaction.importe).label("total"),
            func.count(Transaction.id).label("num"),
        )
        .outerjoin(Category, Transaction.categoria_id == Category.id)
        .filter(
            and_(
                Transaction.fecha >= start_date,
                Transaction.fecha <= end_date,
                Transaction.importe < 0,
                or_(Category.id.is_(None), Category.incluida_en_analisis == True),  # noqa: E712
            )
        )
        .group_by(Transaction.categoria_id, Category.nombre, Category.color)
        .order_by(func.sum(Transaction.importe))
        .all()
    )
    total_expenses = sum((abs(Decimal(str(row.total))) for row in rows), Decimal("0")) or Decimal("1")
    return [
        CategoryExpense(
            categoria_id=row.categoria_id,
            categoria_nombre=row.nombre or "Sin categoría",
            color=row.color,
            importe=abs(Decimal(str(row.total))),
            porcentaje=round(float(abs(Decimal(str(row.total))) / total_expenses * 100), 1),
            num_transacciones=row.num,
        )
        for row in rows
    ]


@router.get("/", response_model=DashboardData)
def get_dashboard(
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    today = date.today()
    selected_year = year or today.year
    selected_month = month or today.month
    if (year is None) != (month is None):
        raise HTTPException(status_code=400, detail="year y month deben enviarse juntos")
    if (selected_year, selected_month) > (today.year, today.month):
        raise HTTPException(status_code=400, detail="No se puede consultar un mes futuro")
    if is_before_min_month(selected_year, selected_month):
        raise HTTPException(status_code=400, detail="No hay datos anteriores al mes mínimo soportado")

    selected_last_day = date(selected_year, selected_month, monthrange(selected_year, selected_month)[1])

    accounts = (
        db.query(Account)
        .filter(Account.activa == True, Account.visible_dashboard == True)  # noqa: E712
        .order_by(Account.id)
        .all()
    )
    balances: dict[int, Decimal] = {}
    for account in accounts:
        future_movements = db.query(func.coalesce(func.sum(Transaction.importe), 0)).filter(
            Transaction.account_id == account.id,
            Transaction.fecha > selected_last_day,
        ).scalar()
        balances[account.id] = account.saldo_actual - Decimal(str(future_movements))

    saldo_total = sum(balances.values(), Decimal("0"))

    saldo_por_cuenta = [
        AccountBalance(
            account=AccountOut.model_validate(a),
            saldo=balances[a.id],
            variacion_mes=Decimal("0.00"),
        )
        for a in accounts
    ]

    prev_month = selected_month - 1 if selected_month > 1 else 12
    prev_year = selected_year if selected_month > 1 else selected_year - 1

    resumen_actual = _monthly_summary(db, selected_year, selected_month)
    resumen_anterior = _monthly_summary(db, prev_year, prev_month)

    month_start = date(selected_year, selected_month, 1)
    gastos_por_categoria = _category_expenses(db, month_start, selected_last_day)
    gastos_por_categoria_anual = _category_expenses(
        db,
        date(selected_year, 1, 1),
        selected_last_day,
    )

    evolucion = []
    for i in range(11, -1, -1):
        m = selected_month - i
        y = selected_year
        while m <= 0:
            m += 12
            y -= 1
        if is_before_min_month(y, m):
            continue
        evolucion.append(_monthly_summary(db, y, m))

    return DashboardData(
        saldo_total=saldo_total,
        saldo_por_cuenta=saldo_por_cuenta,
        resumen_mes_actual=resumen_actual,
        resumen_mes_anterior=resumen_anterior,
        gastos_por_categoria=gastos_por_categoria,
        gastos_por_categoria_anual=gastos_por_categoria_anual,
        evolucion_mensual=evolucion,
    )
