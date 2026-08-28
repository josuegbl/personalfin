from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recurring_income import RecurringIncome
from app.schemas.recurring_income import (
    RecurringIncomeCreate,
    RecurringIncomeResponse,
    RecurringIncomeUpdate,
)

router = APIRouter(prefix="/recurring-income", tags=["recurring-income"])


@router.get("/", response_model=list[RecurringIncomeResponse])
def list_recurring_incomes(db: Session = Depends(get_db)) -> list[RecurringIncomeResponse]:
    """Return all recurring income sources ordered by orden, then id.

    Args:
        db: Database session.

    Returns:
        List of recurring income sources.
    """
    return (
        db.query(RecurringIncome)
        .order_by(RecurringIncome.orden, RecurringIncome.id)
        .all()
    )


@router.post("/", response_model=RecurringIncomeResponse, status_code=201)
def create_recurring_income(
    body: RecurringIncomeCreate,
    db: Session = Depends(get_db),
) -> RecurringIncomeResponse:
    """Create a new recurring income source.

    Args:
        body: Income source data.
        db: Database session.

    Returns:
        The created income source.
    """
    income = RecurringIncome(
        concepto=body.concepto,
        importe=Decimal(str(body.importe)),
        propietario=body.propietario,
        activa=body.activa,
        orden=body.orden,
    )
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


@router.put("/{income_id}", response_model=RecurringIncomeResponse)
def update_recurring_income(
    income_id: int,
    body: RecurringIncomeUpdate,
    db: Session = Depends(get_db),
) -> RecurringIncomeResponse:
    """Update an existing recurring income source.

    Args:
        income_id: ID of the income source to update.
        body: Updated income source data.
        db: Database session.

    Returns:
        The updated income source.

    Raises:
        HTTPException: If the income source is not found.
    """
    income = db.query(RecurringIncome).filter(RecurringIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Ingreso recurrente no encontrado")

    income.concepto = body.concepto
    income.importe = Decimal(str(body.importe))
    income.propietario = body.propietario
    income.activa = body.activa
    income.orden = body.orden

    db.commit()
    db.refresh(income)
    return income


@router.delete("/{income_id}", status_code=204)
def delete_recurring_income(
    income_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete a recurring income source.

    Args:
        income_id: ID of the income source to delete.
        db: Database session.

    Raises:
        HTTPException: If the income source is not found.
    """
    income = db.query(RecurringIncome).filter(RecurringIncome.id == income_id).first()
    if not income:
        raise HTTPException(status_code=404, detail="Ingreso recurrente no encontrado")

    db.delete(income)
    db.commit()
