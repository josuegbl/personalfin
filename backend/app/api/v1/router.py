from fastapi import APIRouter
from app.api.v1 import accounts, categories, dashboard, forecast, recurring_expenses, sync, transactions

router = APIRouter(prefix="/api/v1")

router.include_router(accounts.router)
router.include_router(transactions.router)
router.include_router(categories.router)
router.include_router(dashboard.router)
router.include_router(sync.router)
router.include_router(forecast.router)
router.include_router(recurring_expenses.router)
