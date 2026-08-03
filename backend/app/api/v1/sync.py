from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.account import Account, AccountType
from app.services.sync.bbva import BBVAAdapter
from app.services.sync.eurocaja import EurocajaAdapter
from app.services.sync.paypal import PayPalAdapter

router = APIRouter(prefix="/sync", tags=["sync"])

ADAPTERS = {
    "BBVA": BBVAAdapter,
    "Eurocaja Rural": EurocajaAdapter,
    "PayPal": PayPalAdapter,
}


def _run_sync(account_id: int):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return
        adapter_cls = ADAPTERS.get(account.proveedor)
        if not adapter_cls:
            return
        adapter = adapter_cls(account, db)
        adapter.sync()
    finally:
        db.close()


@router.post("/{account_id}")
def trigger_sync(account_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    background_tasks.add_task(_run_sync, account_id)
    return {"status": "sync_started", "account_id": account_id, "proveedor": account.proveedor}


@router.post("/")
def trigger_all_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.activa == True).all()
    for account in accounts:
        background_tasks.add_task(_run_sync, account.id)
    return {"status": "sync_started", "accounts": len(accounts)}
