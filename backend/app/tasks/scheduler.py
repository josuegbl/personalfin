from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def _daily_sync():
    from app.core.database import SessionLocal
    from app.models.account import Account
    from app.services.sync.bbva import BBVAAdapter
    from app.services.sync.eurocaja import EurocajaAdapter
    from app.services.recurring import detect_recurring

    ADAPTERS = {"BBVA": BBVAAdapter, "Eurocaja Rural": EurocajaAdapter}

    db = SessionLocal()
    try:
        accounts = db.query(Account).filter(Account.activa == True).all()
        for account in accounts:
            adapter_cls = ADAPTERS.get(account.proveedor)
            if not adapter_cls:
                continue
            try:
                adapter = adapter_cls(account, db)
                adapter.sync()
            except Exception as e:
                print(f"[sync] Error en {account.proveedor}: {e}")

        detect_recurring(db)
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    # Sincronización diaria a las 7:00
    scheduler.add_job(_daily_sync, CronTrigger(hour=7, minute=0), id="daily_sync", replace_existing=True)
    scheduler.start()
    return scheduler
