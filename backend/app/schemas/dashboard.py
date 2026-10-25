from decimal import Decimal
from pydantic import BaseModel
from app.schemas.account import AccountOut


class AccountBalance(BaseModel):
    account: AccountOut
    saldo: Decimal
    variacion_mes: Decimal


class MonthlySummary(BaseModel):
    anio: int
    mes: int
    ingresos: Decimal
    gastos: Decimal
    ahorro: Decimal
    num_transacciones: int


class CategoryExpense(BaseModel):
    categoria_id: int | None
    categoria_nombre: str
    color: str | None
    importe: Decimal
    porcentaje: float
    num_transacciones: int


class DashboardData(BaseModel):
    saldo_total: Decimal
    saldo_por_cuenta: list[AccountBalance]
    resumen_mes_actual: MonthlySummary
    resumen_mes_anterior: MonthlySummary
    gastos_por_categoria: list[CategoryExpense]
    gastos_por_categoria_anual: list[CategoryExpense]
    evolucion_mensual: list[MonthlySummary]
