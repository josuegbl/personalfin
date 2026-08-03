from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.transaction import TransactionOrigin
from app.schemas.category import CategoryOut


class TransactionBase(BaseModel):
    account_id: int
    fecha: date
    importe: Decimal
    concepto_original: str
    comercio: str | None = None
    categoria_id: int | None = None
    subcategoria: str | None = None
    recurrente: bool = False
    origen: TransactionOrigin = TransactionOrigin.bank
    paypal_transaction_id: str | None = None
    excluir_de_gastos: bool = False
    notas: str | None = None


class TransactionCreate(TransactionBase):
    hash: str


class TransactionUpdate(BaseModel):
    categoria_id: int | None = None
    subcategoria: str | None = None
    comercio: str | None = None
    recurrente: bool | None = None
    notas: str | None = None


class TransactionOut(TransactionBase):
    id: int
    hash: str
    created_at: datetime
    categoria: CategoryOut | None = None

    model_config = {"from_attributes": True}


class TransactionFilter(BaseModel):
    account_id: int | None = None
    categoria_id: int | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    comercio: str | None = None
    recurrente: bool | None = None
    excluir_pasthrough: bool = True
    page: int = 1
    page_size: int = 50
