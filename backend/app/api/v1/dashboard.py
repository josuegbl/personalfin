from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from app.core.database import get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.category import Category
from app.schemas.dashboard import DashboardData, AccountBalance, MonthlySummary, CategoryExpense
from app.schemas.account import AccountOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _monthly_summary(db: Session, year: int, month: int) -> MonthlySummary:
    q = db.query(
        func.coalesce(func.sum(Transaction.importe).filter(Transaction.importe > 0), 0),
        func.coalesce(func.sum(Transaction.importe).filter(Transaction.importe < 0), 0),
        func.count(Transaction.id),
    ).filter(
        and_(
            extract("year", Transaction.fecha) == year,
            extract("month", Transaction.fecha) == month,
            Transaction.excluir_de_gastos == False,
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


@router.get("/", response_model=DashboardData)
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    year, month = today.year, today.month

    accounts = db.query(Account).filter(Account.activa == True).order_by(Account.id).all()
    saldo_total = sum(a.saldo_actual for a in accounts)

    saldo_por_cuenta = [
        AccountBalance(
            account=AccountOut.model_validate(a),
            saldo=a.saldo_actual,
            variacion_mes=Decimal("0.00"),
        )
        for a in accounts
    ]

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1

    resumen_actual = _monthly_summary(db, year, month)
    resumen_anterior = _monthly_summary(db, prev_year, prev_month)

    cat_rows = (
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
                extract("year", Transaction.fecha) == year,
                extract("month", Transaction.fecha) == month,
                Transaction.importe < 0,
                Transaction.excluir_de_gastos == False,
            )
        )
        .group_by(Transaction.categoria_id, Category.nombre, Category.color)
        .order_by(func.sum(Transaction.importe))
        .all()
    )

    total_gastos = resumen_actual.gastos or Decimal("1")
    gastos_por_categoria = [
        CategoryExpense(
            categoria_id=row.categoria_id,
            categoria_nombre=row.nombre or "Sin categoría",
            color=row.color,
            importe=abs(Decimal(str(row.total))),
            porcentaje=round(float(abs(Decimal(str(row.total))) / total_gastos * 100), 1),
            num_transacciones=row.num,
        )
        for row in cat_rows
    ]

    evolucion = []
    for i in range(11, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        evolucion.append(_monthly_summary(db, y, m))

    return DashboardData(
        saldo_total=saldo_total,
        saldo_por_cuenta=saldo_por_cuenta,
        resumen_mes_actual=resumen_actual,
        resumen_mes_anterior=resumen_anterior,
        gastos_por_categoria=gastos_por_categoria,
        evolucion_mensual=evolucion,
    )
