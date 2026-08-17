from fastapi import APIRouter
from app.api.v1 import accounts, transactions, categories, dashboard, sync, forecast

router = APIRouter(prefix="/api/v1")

router.include_router(accounts.router)
router.include_router(transactions.router)
router.include_router(categories.router)
router.include_router(dashboard.router)
router.include_router(sync.router)
router.include_router(forecast.router)
