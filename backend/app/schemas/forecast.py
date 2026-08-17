from pydantic import BaseModel


class ForecastCategoryItem(BaseModel):
    """A single line item with planned and real amounts."""

    nombre: str
    importe_planificado: float
    importe_real: float

    model_config = {"from_attributes": True}


class ForecastCategoryInput(BaseModel):
    """Input for one variable category budget when saving a plan."""

    nombre: str
    importe_planificado: float


class ForecastPlanUpdate(BaseModel):
    """Request body for creating or updating a monthly forecast plan."""

    ingresos_josue: float
    ingresos_adi: float
    ingresos_extra: float
    categorias: list[ForecastCategoryInput]


class ForecastResponse(BaseModel):
    """Complete forecast data for a single month: plan + real execution."""

    anio: int
    mes: int

    # Planned revenues
    ingresos_josue: float
    ingresos_adi: float
    ingresos_extra: float

    # Fixed expenses from recurring_expenses for the month (read-only, importe_real = 0)
    gastos_fijos: list[ForecastCategoryItem]

    # Variable category budgets saved by the user (importe_real = actual category spend)
    gastos_variables: list[ForecastCategoryItem]

    # All actual spending per category for the month (for ejecución detail view)
    gastos_reales_por_categoria: list[ForecastCategoryItem]

    # Computed plan totals
    total_ingresos_plan: float
    total_gastos_fijos_plan: float
    total_gastos_variables_plan: float
    ahorro_estimado: float

    # Real execution totals
    ingresos_reales: float
    total_gastos_reales: float
    ahorro_real: float

    model_config = {"from_attributes": True}
