from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.category import Category
from app.models.forecast import ForecastCategoryBudget
from app.models.recurring_expense import RecurringExpense
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).order_by(Category.padre_id, Category.nombre).all()
    category_ids_with_transactions = {
        category_id
        for (category_id,) in db.query(Transaction.categoria_id)
        .filter(Transaction.categoria_id.is_not(None))
        .distinct()
        .all()
    }
    category_ids_with_children = {
        category_id
        for (category_id,) in db.query(Category.padre_id)
        .filter(Category.padre_id.is_not(None))
        .distinct()
        .all()
    }

    return [
        CategoryOut.model_validate(category).model_copy(
            update={
                "se_puede_eliminar": (
                    category.id not in category_ids_with_transactions
                    and category.id not in category_ids_with_children
                )
            }
        )
        for category in categories
    ]


@router.post("/", response_model=CategoryOut, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    existing_category = db.query(Category).filter(Category.nombre == data.nombre).first()
    if existing_category:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")

    if data.padre_id is not None:
        parent = db.query(Category).filter(Category.id == data.padre_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Categoría padre no encontrada")

    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat).model_copy(update={"se_puede_eliminar": True})


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db)):
    """Rename a category and propagate its legacy stored labels.

    Args:
        category_id: ID of the category to rename.
        data: New category name.
        db: Database session.

    Returns:
        The renamed category.

    Raises:
        HTTPException: If the category is missing or the new name is invalid.
    """
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    new_name = data.nombre.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")

    duplicate = (
        db.query(Category)
        .filter(Category.nombre == new_name, Category.id != category_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")

    old_name = category.nombre
    category.nombre = new_name

    # These text fields predate the category hierarchy. Keep them synchronized
    # so every existing forecast and recurring expense resolves to this rename.
    db.query(ForecastCategoryBudget).filter(
        ForecastCategoryBudget.categoria_nombre == old_name
    ).update({ForecastCategoryBudget.categoria_nombre: new_name}, synchronize_session=False)

    if category.padre_id is None:
        db.query(RecurringExpense).filter(
            RecurringExpense.categoria == old_name
        ).update({RecurringExpense.categoria: new_name}, synchronize_session=False)
    else:
        db.query(RecurringExpense).filter(
            RecurringExpense.subcategoria_id == category_id
        ).update({RecurringExpense.concepto: new_name}, synchronize_session=False)

    db.commit()
    db.refresh(category)
    return CategoryOut.model_validate(category).model_copy(
        update={
            "se_puede_eliminar": (
                not category.transactions and not category.subcategorias
            )
        }
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")

    has_transactions = (
        db.query(Transaction.id)
        .filter(Transaction.categoria_id == category_id)
        .first()
        is not None
    )
    if has_transactions:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar una categoría con movimientos asociados",
        )

    has_children = db.query(Category.id).filter(Category.padre_id == category_id).first() is not None
    if has_children:
        raise HTTPException(
            status_code=409,
            detail="Elimina primero las subcategorías de esta categoría",
        )

    db.query(RecurringExpense).filter(
        RecurringExpense.subcategoria_id == category_id
    ).update({RecurringExpense.subcategoria_id: None}, synchronize_session=False)
    db.delete(category)
    db.commit()
