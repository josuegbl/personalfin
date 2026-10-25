from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import date
from app.core.database import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionOut, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionOut])
def list_transactions(
    account_id: int | None = Query(None),
    categoria_id: int | None = Query(None),
    fecha_desde: date | None = Query(None),
    fecha_hasta: date | None = Query(None),
    comercio: str | None = Query(None),
    concepto: str | None = Query(None),
    tipo: str | None = Query(None, pattern="^(ingresos|gastos)$"),
    recurrente: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    filters = []

    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if categoria_id is not None:
        filters.append(Transaction.categoria_id == categoria_id)
    if fecha_desde:
        filters.append(Transaction.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(Transaction.fecha <= fecha_hasta)
    if comercio:
        filters.append(Transaction.comercio.ilike(f"%{comercio}%"))
    if concepto:
        search_filter = f"%{concepto}%"
        filters.append(or_(
            Transaction.concepto_original.ilike(search_filter),
            Transaction.comercio.ilike(search_filter),
        ))
    if tipo == "ingresos":
        filters.append(Transaction.importe > 0)
    elif tipo == "gastos":
        filters.append(Transaction.importe < 0)
    if recurrente is not None:
        filters.append(Transaction.recurrente == recurrente)
    if filters:
        q = q.filter(and_(*filters))

    total = q.count()
    items = q.order_by(Transaction.fecha.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return t


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(transaction_id: int, data: TransactionUpdate, db: Session = Depends(get_db)):
    t = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return t
