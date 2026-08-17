from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models.recurring_expense import RecurringExpense, RecurringExpenseTier
from app.schemas.recurring_expense import RecurringExpenseCreate, RecurringExpenseOut, RecurringExpenseUpdate

router = APIRouter(prefix="/recurring-expenses", tags=["recurring-expenses"])


def _load(expense_id: int, db: Session) -> RecurringExpense:
    """Fetch a RecurringExpense by ID with its tiers eagerly loaded.

    Args:
        expense_id: Primary key of the expense to fetch.
        db: Database session.

    Returns:
        The loaded RecurringExpense.

    Raises:
        HTTPException: 404 if the expense does not exist.
    """
    expense = (
        db.query(RecurringExpense)
        .options(selectinload(RecurringExpense.tiers))
        .filter(RecurringExpense.id == expense_id)
        .first()
    )
    if expense is None:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    return expense


def _replace_tiers(expense: RecurringExpense, tiers_in, db: Session) -> None:
    """Delete all existing tiers for an expense and insert new ones.

    Args:
        expense: The expense whose tiers to replace.
        tiers_in: Iterable of TierIn objects with importe and meses.
        db: Database session.
    """
    for t in list(expense.tiers):
        db.delete(t)
    db.flush()
    for tier in tiers_in:
        db.add(RecurringExpenseTier(
            expense_id=expense.id,
            importe=Decimal(str(tier.importe)),
            meses=tier.meses,
        ))


@router.post("/", response_model=RecurringExpenseOut, status_code=201)
def create_recurring_expense(body: RecurringExpenseCreate, db: Session = Depends(get_db)) -> RecurringExpense:
    """Create a new recurring fixed expense with one or more price tiers.

    Args:
        body: Expense data including at least one price tier.
        db: Database session.

    Returns:
        The created expense with its tiers.
    """
    expense = RecurringExpense(concepto=body.concepto, importe=Decimal("0"), tipo="fijo")
    db.add(expense)
    db.flush()
    for tier in body.tiers:
        db.add(RecurringExpenseTier(
            expense_id=expense.id,
            importe=Decimal(str(tier.importe)),
            meses=tier.meses,
        ))
    db.commit()
    return _load(expense.id, db)


@router.patch("/{expense_id}", response_model=RecurringExpenseOut)
def update_recurring_expense(expense_id: int, body: RecurringExpenseUpdate, db: Session = Depends(get_db)) -> RecurringExpense:
    """Update a recurring expense name and replace all its price tiers.

    Args:
        expense_id: ID of the expense to update.
        body: New name and complete list of tiers (replaces existing tiers).
        db: Database session.

    Returns:
        The updated expense with its tiers.

    Raises:
        HTTPException: 404 if the expense does not exist.
    """
    expense = _load(expense_id, db)
    expense.concepto = body.concepto
    _replace_tiers(expense, body.tiers, db)
    db.commit()
    return _load(expense.id, db)


@router.delete("/{expense_id}", status_code=204)
def delete_recurring_expense(expense_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a recurring expense and all its tiers.

    Args:
        expense_id: ID of the recurring expense to remove.
        db: Database session.

    Raises:
        HTTPException: 404 if the expense does not exist.
    """
    expense = db.get(RecurringExpense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Recurring expense not found")
    db.delete(expense)
    db.commit()
