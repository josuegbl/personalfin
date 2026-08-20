from pydantic import BaseModel


class RecurringIncomeBase(BaseModel):
    """Shared fields for recurring income requests."""

    concepto: str
    importe: float
    propietario: str | None = None
    activa: bool = True
    orden: int = 0


class RecurringIncomeCreate(RecurringIncomeBase):
    """Request body for creating a recurring income source."""


class RecurringIncomeUpdate(RecurringIncomeBase):
    """Request body for updating a recurring income source."""


class RecurringIncomeResponse(RecurringIncomeBase):
    """Response schema for a recurring income source."""

    id: int

    model_config = {"from_attributes": True}
