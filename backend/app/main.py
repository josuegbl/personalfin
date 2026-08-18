from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router
from app.core.database import engine, Base
import app.models  # noqa: F401 – registra todos los modelos en Base.metadata

app = FastAPI(
    title="BankFinances API",
    description="API de gestión de economía familiar",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://192.168.1.51:5173",
        "http://192.168.1.51:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    _seed_categories()
    _seed_recurring_expenses()


def _seed_categories():
    from app.core.database import SessionLocal
    from app.models.category import Category, CategorizationRule

    # (nombre, icono, color, es_compartida_por_defecto)
    CATEGORIAS = [
        ("Vivienda", "🏠", "#6366f1", True),
        ("Alimentación", "🛒", "#22c55e", True),
        ("Supermercado", "🛒", "#16a34a", True),
        ("Gasolina", "⛽", "#f97316", False),
        ("Transporte", "🚗", "#f59e0b", False),
        ("Restaurantes", "🍽️", "#ec4899", False),
        ("Ocio", "🎬", "#8b5cf6", False),
        ("Salud", "💊", "#ef4444", False),
        ("Educación", "📚", "#0ea5e9", True),
        ("Seguros", "🛡️", "#64748b", True),
        ("Impuestos", "🏛️", "#94a3b8", True),
        ("Nómina", "💼", "#10b981", False),
        ("Transferencias internas", "↔️", "#a3a3a3", False),
        ("Suscripciones", "🔄", "#7c3aed", False),
        ("PayPal", "💙", "#0070ba", False),
        ("Otros", "📦", "#d1d5db", False),
    ]

    REGLAS = [
        ("MERCADONA", "Supermercado"),
        ("CARREFOUR", "Supermercado"),
        ("DIA ", "Supermercado"),
        ("LIDL", "Supermercado"),
        ("ALCAMPO", "Supermercado"),
        ("REPSOL", "Gasolina"),
        ("CEPSA", "Gasolina"),
        ("BP ", "Gasolina"),
        ("GALP", "Gasolina"),
        ("NETFLIX", "Suscripciones"),
        ("SPOTIFY", "Suscripciones"),
        ("AMAZON PRIME", "Suscripciones"),
        ("HBO", "Suscripciones"),
        ("DISNEY", "Suscripciones"),
        ("PAYPAL", "PayPal"),
        ("HIPOTECA", "Vivienda"),
        ("COMUNIDAD", "Vivienda"),
        ("IBERDROLA", "Vivienda"),
        ("ENDESA", "Vivienda"),
        ("NATURGY", "Vivienda"),
        ("VODAFONE", "Vivienda"),
        ("MOVISTAR", "Vivienda"),
        ("ORANGE", "Vivienda"),
        ("FARMACIA", "Salud"),
        ("AMAZON", "Ocio"),
    ]

    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            return

        cat_map = {}
        for nombre, icono, color, compartida in CATEGORIAS:
            cat = Category(nombre=nombre, icono=icono, color=color, es_compartida_por_defecto=compartida)
            db.add(cat)
            db.flush()
            cat_map[nombre] = cat.id

        for patron, cat_nombre in REGLAS:
            rule = CategorizationRule(
                patron=patron,
                categoria_id=cat_map[cat_nombre],
                prioridad=10,
            )
            db.add(rule)

        db.commit()
    finally:
        db.close()


def _seed_recurring_expenses():
    from app.core.database import SessionLocal
    from app.models.recurring_expense import RecurringExpense, RecurringExpenseTier
    from app.seed import RECURRING_EXPENSES

    db = SessionLocal()
    try:
        if db.query(RecurringExpense).count() > 0:
            return
        for data in RECURRING_EXPENSES:
            tiers_data = data.get("tiers", [])
            expense_data = {k: v for k, v in data.items() if k != "tiers"}
            if "importe" not in expense_data and tiers_data:
                catchall = next((t for t in tiers_data if t.get("meses") is None), tiers_data[0])
                expense_data["importe"] = catchall["importe"]
            expense = RecurringExpense(**expense_data)
            expense.tiers = [RecurringExpenseTier(**t) for t in tiers_data]
            db.add(expense)
        db.commit()
    finally:
        db.close()
