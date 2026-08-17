from decimal import Decimal
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.account import Account
from app.services.sync.base import CSVImportAdapter
from app.services.sync.bbva import BBVAAdapter, BBVAPlaywrightAdapter
from app.services.sync.eurocaja import EurocajaAdapter
from app.services.sync.paypal import PayPalAdapter, mark_bank_passthroughs

router = APIRouter(prefix="/sync", tags=["sync"])

# Mapa de parsers CSV por proveedor
CSV_PARSERS = {
    "BBVA": BBVAAdapter.parse_csv_upload,
    "Eurocaja Rural": EurocajaAdapter.parse_csv_upload,
}

# Mapa de adaptadores automáticos
AUTO_ADAPTERS = {
    "PayPal": PayPalAdapter,
    "BBVA":   BBVAPlaywrightAdapter,
}


# ------------------------------------------------------------------
# Upload CSV (BBVA y Eurocaja)
# ------------------------------------------------------------------

@router.post("/{account_id}/upload")
async def upload_csv(
    account_id: int,
    file: UploadFile = File(...),
    balance: Decimal | None = Form(None),
    db: Session = Depends(get_db),
):
    """
    Importa un extracto CSV o Excel descargado manualmente desde el banco.

    Acepta .csv (BBVA, Eurocaja) y .xlsx (BBVA Excel). El saldo se extrae
    automáticamente del archivo cuando está disponible. El parámetro ``balance``
    lo sobreescribe si se indica explícitamente.
    """
    from app.services.sync.bbva import parse_bbva_excel

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    raw_content = await file.read()
    filename = (file.filename or "").lower()

    # Excel de BBVA (.xlsx): no requiere decodificación de texto
    if filename.endswith(".xlsx"):
        if account.proveedor != "BBVA":
            raise HTTPException(
                status_code=400,
                detail=f"El formato .xlsx solo está soportado para BBVA (proveedor actual: {account.proveedor!r})",
            )
        try:
            transactions, detected_balance = parse_bbva_excel(raw_content)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Error parseando Excel BBVA: {exc}")
    else:
        parser = CSV_PARSERS.get(account.proveedor)
        if not parser:
            raise HTTPException(
                status_code=400,
                detail=f"El proveedor '{account.proveedor}' no soporta importación CSV. "
                       f"Proveedores soportados: {', '.join(CSV_PARSERS)}",
            )

        # Intentar utf-8-sig primero (maneja BOM, habitual en Eurocaja),
        # luego utf-8 puro, finalmente latin-1 como fallback para bancos legacy.
        # latin-1 nunca falla pero da texto corrupto con UTF-8, por eso va al final.
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                content = raw_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=422, detail="No se pudo decodificar el archivo CSV")

        try:
            transactions, detected_balance = parser(content)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Error parseando CSV: {exc}")

    final_balance = balance or detected_balance or account.saldo_actual

    adapter = CSVImportAdapter(account, db, transactions, final_balance)
    imported = adapter.sync()

    # Actualizar marcado de passthroughs PayPal en cuentas bancarias:
    # los cargos "RECIBO PayPal..." quedan excluidos de gastos porque el
    # gasto real se registra en PayPal.
    paypal_marked = mark_bank_passthroughs(db)

    return {
        "imported": imported,
        "total_in_file": len(transactions),
        "skipped_duplicates": len(transactions) - imported,
        "balance": float(final_balance),
        "paypal_passthroughs_marked": paypal_marked,
    }


# ------------------------------------------------------------------
# Sync automático (solo PayPal)
# ------------------------------------------------------------------

def _run_auto_sync(account_id: int):
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return

        adapter_cls = AUTO_ADAPTERS.get(account.proveedor)
        if not adapter_cls:
            account.sync_error = (
                f"'{account.proveedor}' no tiene sync automático. "
                "Usa el endpoint de upload CSV."
            )
            db.commit()
            return

        try:
            adapter = adapter_cls(account, db)
            adapter.sync()
            account.sync_error = None
            db.commit()
        except Exception as exc:
            db.rollback()
            account = db.query(Account).filter(Account.id == account_id).first()
            if account:
                account.sync_error = str(exc)[:500]
                db.commit()
    finally:
        db.close()


@router.post("/{account_id}")
def trigger_sync(account_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Sync automático vía API (solo disponible para PayPal)."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if account.proveedor not in AUTO_ADAPTERS:
        raise HTTPException(
            status_code=400,
            detail=f"'{account.proveedor}' usa importación CSV. Usa POST /sync/{account_id}/upload",
        )
    background_tasks.add_task(_run_auto_sync, account_id)
    return {"status": "sync_started", "account_id": account_id, "proveedor": account.proveedor}


@router.post("/")
def trigger_all_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Sync automático para todos los proveedores que lo soporten (PayPal)."""
    accounts = (
        db.query(Account)
        .filter(Account.activa == True, Account.proveedor.in_(AUTO_ADAPTERS.keys()))
        .all()
    )
    for account in accounts:
        background_tasks.add_task(_run_auto_sync, account.id)
    return {"status": "sync_started", "accounts": len(accounts)}


@router.get("/status")
def sync_status(db: Session = Depends(get_db)):
    """Estado de la última sincronización de cada cuenta."""
    accounts = db.query(Account).filter(Account.activa == True).order_by(Account.id).all()
    return [
        {
            "account_id": a.id,
            "alias": a.alias,
            "proveedor": a.proveedor,
            "ultima_sync": a.ultima_sync,
            "sync_error": a.sync_error,
            "sync_mode": "auto" if a.proveedor in AUTO_ADAPTERS else "csv_upload",
        }
        for a in accounts
    ]
