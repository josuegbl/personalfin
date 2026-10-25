from pydantic import BaseModel


class FixedExpenseTier(BaseModel):
    """Price tier data embedded in forecast response for editing."""

    importe: float
    meses: list[int] | None


class ForecastCategoryItem(BaseModel):
    """A single line item with planned and real amounts."""

    id: int | None = None
    categoria: str | None = None
    nombre: str
    importe_planificado: float
    importe_real: float
    meses: list[int] | None = None
    tiers: list[FixedExpenseTier] = []

    model_config = {"from_attributes": True}


class ForecastCategoryInput(BaseModel):
    """Input for one variable category budget when saving a plan."""

    nombre: str
    importe_planificado: float


class FixedCategoryGroup(BaseModel):
    """Grouped fixed expenses by parent category."""

    categoria: str
    subcategorias: list[ForecastCategoryItem]


class ForecastPlanUpdate(BaseModel):
    """Request body for creating or updating a monthly forecast plan."""

    cuenta_personal_a: float
    cuenta_personal_b: float
    ingresos_planificados: float | None = None
    ingresos_persona_a: float
    ingresos_persona_b: float
    categorias: list[ForecastCategoryInput]


class ForecastResponse(BaseModel):
    """Complete forecast data for a single month: plan + real execution.

    Income rule:
      - ingresos_nomina: salaries received in month M-1. They are available
        income for month M.
      - ingresos_otros: all other positive non-excluded transactions from month M
        (refunds, miscellaneous transfers, etc.) counted in the current month.
      - ingresos_reales: total available income = nomina + otros.
    """

    anio: int
    mes: int
    es_ejecucion: bool
    balance_cerrado: bool

    # Personal budget allocations; treated as a separate expense in execution.
    cuenta_personal_a: float
    cuenta_personal_b: float

    # User-editable planned income (gross nóminas). None = no manual override.
    ingresos_planificados: float | None
    ingresos_persona_a: float
    ingresos_persona_b: float

    # Income breakdown (computed from actual transactions)
    ingresos_nomina: float   # Salaries from M-1
    ingresos_otros: float    # Other income from current month M
    ingresos_reales: float   # Total = nomina + otros

    # Fixed expenses from recurring_expenses (read-only)
    gastos_fijos: list[ForecastCategoryItem]
    gastos_fijos_por_categoria: list[FixedCategoryGroup]

    # Variable category budgets saved by the user
    gastos_variables: list[ForecastCategoryItem]

    # All actual spending per category for the month
    gastos_reales_por_categoria: list[ForecastCategoryItem]

    # Computed totals
    total_cuentas_personales_plan: float
    total_gastos_fijos_plan: float
    total_gastos_variables_plan: float
    ahorro_estimado: float   # planned salaries - personal - fixed - variable expenses

    total_gastos_reales: float  # Transaction expenses plus personal allocations
    ahorro_real: float       # ingresos_reales - gastos_reales

    model_config = {"from_attributes": True}
