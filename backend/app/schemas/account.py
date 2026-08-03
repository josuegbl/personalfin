from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.account import AccountType


class AccountBase(BaseModel):
    tipo: AccountType
    proveedor: str
    iban: str | None = None
    alias: str
    moneda: str = "EUR"
    propietario: str | None = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    alias: str | None = None
    saldo_actual: Decimal | None = None
    activa: bool | None = None
    propietario: str | None = None


class AccountOut(AccountBase):
    id: int
    saldo_actual: Decimal
    activa: bool
    ultima_sync: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
