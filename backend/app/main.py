from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router
from app.core.database import engine, Base
from app.seed import ensure_forecast_catalog
import app.models  # noqa: F401 – registra todos los modelos en Base.metadata

app = FastAPI(
    title="BankFinances API",
    description="API de gestión de economía familiar",
    version="1.0.0",
    redirect_slashes=False,
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
    ensure_forecast_catalog()


def _seed_categories():
    from app.core.database import SessionLocal
    from app.models.category import Category

    # (nombre, icono, color, compartida, naturaleza, incluida_en_analisis)
    CATEGORIAS = [
        ("Vivienda", "🏠", "#6366f1", True, "gasto", True),
        ("Alimentación", "🛒", "#22c55e", True, "gasto", True),
        ("Supermercado", "🛒", "#16a34a", True, "gasto", True),
        ("Gasolina", "⛽", "#f97316", False, "gasto", True),
        ("Transporte", "🚗", "#f59e0b", False, "gasto", True),
        ("Restaurantes", "🍽️", "#ec4899", False, "gasto", True),
        ("Ocio", "🎬", "#8b5cf6", False, "gasto", True),
        ("Salud", "💊", "#ef4444", False, "gasto", True),
        ("Educación", "📚", "#0ea5e9", True, "gasto", True),
        ("Seguros", "🛡️", "#64748b", True, "gasto", True),
        ("Impuestos", "🏛️", "#94a3b8", True, "gasto", True),
        ("Nómina", "💼", "#10b981", False, "ingreso", True),
        ("Transferencias", None, "#a3a3a3", False, "transferencia", True),
        ("Sin categoría", "?", "#94a3b8", False, "neutral", True),
        ("Suscripciones", "🔄", "#7c3aed", False, "gasto", True),
        ("Otros", "📦", "#d1d5db", False, "gasto", True),
    ]

    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            return

        for nombre, icono, color, compartida, naturaleza, incluida in CATEGORIAS:
            cat = db.query(Category).filter(Category.nombre == nombre).first()
            if not cat:
                cat = Category(
                    nombre=nombre,
                    icono=icono,
                    color=color,
                    es_compartida_por_defecto=compartida,
                    naturaleza=naturaleza,
                    incluida_en_analisis=incluida,
                )
                db.add(cat)
                db.flush()
            else:
                cat.naturaleza = naturaleza
                cat.incluida_en_analisis = incluida

        transferencias = db.query(Category).filter(Category.nombre == "Transferencias").first()
        if transferencias:
            transfer_subcategories = [
                ("Entrantes", "ingreso", True),
                ("Salientes", "gasto", True),
                ("Internas", "neutral", False),
            ]
            for nombre, naturaleza, incluida in transfer_subcategories:
                subcategory = db.query(Category).filter(Category.nombre == nombre).first()
                if not subcategory:
                    subcategory = Category(nombre=nombre)
                    db.add(subcategory)
                subcategory.padre_id = transferencias.id
                subcategory.color = transferencias.color
                subcategory.naturaleza = naturaleza
                subcategory.incluida_en_analisis = incluida

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
