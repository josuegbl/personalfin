from pydantic import BaseModel, field_validator


class TierIn(BaseModel):
    """One price tier: amount + which months it applies."""

    importe: float
    meses: list[int] | None  # None = catch-all (any month not covered by other tiers)

    @field_validator("meses")
    @classmethod
    def meses_valid(cls, v: list[int] | None) -> list[int] | None:
        """Validate that month values are within 1–12 and the list is non-empty when provided."""
        if v is not None:
            if not v:
                raise ValueError("meses must have at least one month")
            if any(m < 1 or m > 12 for m in v):
                raise ValueError("months must be 1–12")
        return v


class TierOut(BaseModel):
    """Response for one price tier."""

    id: int
    importe: float
    meses: list[int] | None

    model_config = {"from_attributes": True}


class RecurringExpenseCreate(BaseModel):
    """Request body to create a new recurring expense with its price tiers."""

    concepto: str
    tiers: list[TierIn]

    @field_validator("tiers")
    @classmethod
    def at_least_one_tier(cls, v: list[TierIn]) -> list[TierIn]:
        """Ensure at least one tier is provided."""
        if not v:
            raise ValueError("at least one tier is required")
        return v


class RecurringExpenseUpdate(BaseModel):
    """Request body to update a recurring expense (replaces all tiers)."""

    concepto: str
    tiers: list[TierIn]

    @field_validator("tiers")
    @classmethod
    def at_least_one_tier(cls, v: list[TierIn]) -> list[TierIn]:
        """Ensure at least one tier is provided."""
        if not v:
            raise ValueError("at least one tier is required")
        return v


class RecurringExpenseOut(BaseModel):
    """Response for a recurring expense including all tiers."""

    id: int
    concepto: str
    tipo: str
    tiers: list[TierOut]

    model_config = {"from_attributes": True}
