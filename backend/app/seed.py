"""
Seed inicial: categorías y gastos estacionales conocidos.
Uso: python -m app.seed
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.category_catalog import CATEGORY_CODE_NOMINA, CATEGORY_CODE_SIN_CATEGORIA
from app.core.forecast_catalog import FIXED_CATEGORY_NAMES, SUBSCRIPTION_DEFAULT_CONCEPTS, normalize_fixed_category_name
from app.models.category import Category
from app.models.recurring_expense import RecurringExpense, RecurringExpenseTier


CATEGORIES = [
    {"nombre": "Vivienda",               "icono": "🏠", "color": "#6366f1"},
    {"nombre": "Alimentación",           "icono": "🛒", "color": "#22c55e"},
    {"nombre": "Supermercado",           "icono": "🛒", "color": "#16a34a"},
    {"nombre": "Gasolina",               "icono": "⛽", "color": "#f97316"},
    {"nombre": "Transporte",             "icono": "🚗", "color": "#fb923c"},
    {"nombre": "Restaurantes",           "icono": "🍽️", "color": "#ef4444"},
    {"nombre": "Ocio",                   "icono": "🎮", "color": "#a855f7"},
    {"nombre": "Salud",                  "icono": "💊", "color": "#ec4899"},
    {"nombre": "Educación",              "icono": "📚", "color": "#3b82f6"},
    {"nombre": "Seguros",                "icono": "🛡️", "color": "#0ea5e9"},
    {"nombre": "Impuestos",              "icono": "🏛️", "color": "#64748b"},
    {"nombre": "Nómina",                 "icono": "💰", "color": "#10b981", "naturaleza": "ingreso", "codigo_sistema": CATEGORY_CODE_NOMINA},
    {"nombre": "Transferencias",         "icono": "↔️", "color": "#94a3b8", "naturaleza": "transferencia", "incluida_en_analisis": True},
    {"nombre": "Transferencias Internas", "icono": "↔️", "color": "#94a3b8", "naturaleza": "transferencia", "incluida_en_analisis": True},
    {"nombre": "Sin categoría",         "icono": "?",  "color": "#94a3b8", "naturaleza": "neutral", "incluida_en_analisis": True, "codigo_sistema": CATEGORY_CODE_SIN_CATEGORIA},
    {"nombre": "Suscripciones",          "icono": "📱", "color": "#8b5cf6"},
    {"nombre": "Préstamos",              "icono": "🏦", "color": "#dc2626"},
    {"nombre": "Tarjeta Credito",        "icono": "💳", "color": "#dc2626"},
    {"nombre": "Remesas",                "icono": "💸", "color": "#2563eb"},
    {"nombre": "Colegios",               "icono": "🏫", "color": "#0ea5e9"},
    {"nombre": "Deportes",               "icono": "⚽", "color": "#16a34a"},
    {"nombre": "Otros",                  "icono": "📦", "color": "#9ca3af"},
]

# Gastos fijos y estacionales. Cada entrada tiene una lista de tiers.
# tiers: [{"importe": float, "meses": list[int] | None}]
# meses None = todos los meses (catch-all).
RECURRING_EXPENSES = [
    # --- Fijos todos los meses (single tier, meses=None) ---
    {
        "concepto": "Hipoteca Caja Rural",
        "tipo": "fijo", "dia_cobro": 1, "categoria": "Vivienda",
        "tiers": [{"importe": 550.93, "meses": None}],
    },
    {
        "concepto": "Préstamo BBVA",
        "tipo": "fijo", "dia_cobro": 5, "categoria": "Préstamos",
        "tiers": [{"importe": 30.30, "meses": None}],
    },
    {
        "concepto": "Kia Stonic",
        "tipo": "fijo", "dia_cobro": 5, "categoria": "Préstamos",
        "tiers": [{"importe": 246.04, "meses": None}],
    },
    {
        "concepto": "AA Cetelem",
        "tipo": "fijo", "dia_cobro": 5, "categoria": "Préstamos",
        "tiers": [{"importe": 124.82, "meses": None}],
    },
    {
        "concepto": "Préstamo COFIDIS",
        "tipo": "fijo", "dia_cobro": 5, "categoria": "Préstamos",
        "tiers": [{"importe": 238.40, "meses": None}],
    },
    {
        "concepto": "Préstamo CETELEM",
        "tipo": "fijo", "dia_cobro": 5, "categoria": "Préstamos",
        "tiers": [{"importe": 308.96, "meses": None}],
    },
    {
        "concepto": "Inglés Caja Rural",
        "tipo": "fijo", "dia_cobro": 1, "categoria": "Educación",
        "tiers": [{"importe": 74.22, "meses": None}],
    },
    {
        "concepto": "Móvil + Internet",
        "tipo": "fijo", "dia_cobro": 1, "categoria": "Vivienda",
        "tiers": [{"importe": 109.00, "meses": None}],
    },
    {
        "concepto": "Comunidad",
        "tipo": "fijo", "dia_cobro": 1, "categoria": "Vivienda",
        "tiers": [{"importe": 80.00, "meses": None}],
    },
    {
        "concepto": "Sanitas Dental",
        "tipo": "fijo", "dia_cobro": 1, "categoria": "Salud",
        "tiers": [{"importe": 59.90, "meses": None}],
    },
    {
        "concepto": "Netflix",
        "tipo": "fijo", "dia_cobro": 15, "categoria": "Suscripciones",
        "tiers": [{"importe": 14.99, "meses": None}],
    },
    {
        "concepto": "Disney+",
        "tipo": "fijo", "dia_cobro": 15, "categoria": "Suscripciones",
        "tiers": [{"importe": 10.99, "meses": None}],
    },
    {
        "concepto": "Max",
        "tipo": "fijo", "dia_cobro": 15, "categoria": "Suscripciones",
        "tiers": [{"importe": 7.99, "meses": None}],
    },
    {
        "concepto": "Spotify",
        "tipo": "fijo", "dia_cobro": 15, "categoria": "Suscripciones",
        "tiers": [{"importe": 16.99, "meses": None}],
    },
    {
        "concepto": "HP Printer",
        "tipo": "fijo", "dia_cobro": 15, "categoria": "Suscripciones",
        "tiers": [{"importe": 1.79, "meses": None}],
    },
    {
        "concepto": "Pago personal",
        "tipo": "fijo", "dia_cobro": 1, "categoria": "Otros",
        "tiers": [{"importe": 21.73, "meses": None}],
    },
    # --- Estacionales con múltiples tramos ---
    {
        "concepto": "Luz",
        "tipo": "estacional", "dia_cobro": 15, "categoria": "Vivienda",
        "tiers": [
            {"importe": 150.00, "meses": [7, 8, 9]},
            {"importe": 120.00, "meses": [5, 6, 10, 11]},
            {"importe": 100.00, "meses": [1, 2, 3, 4, 12]},
        ],
    },
    {
        "concepto": "Gas",
        "tipo": "estacional", "dia_cobro": 15, "categoria": "Vivienda",
        "tiers": [
            {"importe": 90.00,  "meses": [6, 8, 10]},
            {"importe": 130.00, "meses": [4, 12]},
            {"importe": 200.00, "meses": [2]},
        ],
    },
    {
        "concepto": "Remesas",
        "tipo": "estacional", "dia_cobro": 15, "categoria": "Otros",
        "tiers": [
            {"importe": 100.00, "meses": [1, 3, 5, 7, 9, 11]},
            {"importe": 200.00, "meses": [4, 6, 8, 10, 12]},
            {"importe": 300.00, "meses": [2]},
        ],
    },
    # --- Estacionales de tramo único ---
    {
        "concepto": "Agua (bimestral)",
        "tipo": "estacional", "dia_cobro": 15, "categoria": "Vivienda",
        "tiers": [{"importe": 50.00, "meses": [1, 3, 5, 7, 9, 11]}],
    },
    {
        "concepto": "Comedor colegio",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Educación",
        "tiers": [{"importe": 121.00, "meses": [2, 3, 4, 5, 6]}],
    },
    {
        "concepto": "Comedor colegio (inicio)",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Educación",
        "tiers": [{"importe": 242.00, "meses": [10]}],
    },
    {
        "concepto": "Seguro Toyota",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Seguros",
        "tiers": [{"importe": 471.64, "meses": [9]}],
    },
    {
        "concepto": "Seguro Kia",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Seguros",
        "tiers": [{"importe": 121.82, "meses": [2, 4]}],
    },
    {
        "concepto": "Seguro Hogar",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Seguros",
        "tiers": [{"importe": 98.12, "meses": [2, 5, 8, 11]}],
    },
    {
        "concepto": "Seguro Vida",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Seguros",
        "tiers": [{"importe": 121.91, "meses": [2, 5, 8, 11]}],
    },
    {
        "concepto": "Amazon Prime",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Suscripciones",
        "tiers": [{"importe": 49.99, "meses": [9]}],
    },
    {
        "concepto": "Microsoft 365",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Suscripciones",
        "tiers": [{"importe": 129.99, "meses": [8]}],
    },
    {
        "concepto": "Mantenimiento caldera",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Vivienda",
        "tiers": [{"importe": 155.05, "meses": [5]}],
    },
    {
        "concepto": "Comisión tarjeta",
        "tipo": "estacional", "dia_cobro": 1, "categoria": "Otros",
        "tiers": [{"importe": 80.00, "meses": [7]}],
    },
]


def recurring_expense_category_id(db: Session, parent_name: str, concept: str) -> int:
    normalized_parent = normalize_fixed_category_name(parent_name)
    parent = (
        db.query(Category)
        .filter(Category.nombre == normalized_parent, Category.padre_id.is_(None))
        .first()
    )
    if parent is None:
        raise ValueError(f"Categoría padre no encontrada para gasto recurrente: {normalized_parent}")

    subcategory = (
        db.query(Category)
        .filter(Category.nombre == concept, Category.padre_id == parent.id)
        .first()
    )
    return subcategory.id if subcategory is not None else parent.id


def ensure_category_system_codes(db: Session) -> None:
    for name, code in (
        ("Nómina", CATEGORY_CODE_NOMINA),
        ("Sin categoría", CATEGORY_CODE_SIN_CATEGORIA),
    ):
        category = db.query(Category).filter(Category.nombre == name).first()
        if category is not None and category.codigo_sistema != code:
            category.codigo_sistema = code


def seed():
    """Populate the database with default categories and recurring expenses.

    Only inserts recurring expenses when the table is empty, so it is safe
    to call on every startup.
    """
    db = SessionLocal()
    try:
        existing = {c.nombre for c in db.query(Category).all()}
        for data in CATEGORIES:
            if data["nombre"] not in existing:
                db.add(Category(**data))
        db.flush()

        if db.query(RecurringExpense).count() == 0:
            for data in RECURRING_EXPENSES:
                tiers_data = data["tiers"]
                parent_name = data["categoria"]
                expense_data = {
                    k: v for k, v in data.items() if k not in {"tiers", "categoria"}
                }
                expense_data["subcategoria_id"] = recurring_expense_category_id(
                    db, parent_name, data["concepto"]
                )
                expense = RecurringExpense(**expense_data, importe=Decimal("0"))
                db.add(expense)
                db.flush()
                for tier in tiers_data:
                    db.add(RecurringExpenseTier(
                        expense_id=expense.id,
                        importe=Decimal(str(tier["importe"])),
                        meses=tier["meses"],
                    ))

        ensure_category_system_codes(db)
        db.commit()
        print("Seed completado.")
    finally:
        db.close()


def ensure_forecast_catalog() -> None:
    """Guarantee fixed forecast categories and base subscription concepts exist.

    This runs on every startup and is idempotent.
    """
    db = SessionLocal()
    try:
        parent_categories: dict[str, Category] = {}

        for category_name in FIXED_CATEGORY_NAMES:
            normalized = normalize_fixed_category_name(category_name)
            category = db.query(Category).filter(Category.nombre == normalized).first()
            if category is None:
                category = Category(
                    nombre=normalized,
                    icono="📁",
                    color="#6b7280",
                    naturaleza="gasto",
                    incluida_en_analisis=True,
                )
                db.add(category)
                db.flush()
            category.padre_id = None
            parent_categories[normalized] = category

        subscriptions_parent = parent_categories.get("Suscripciones")
        if subscriptions_parent is not None:
            for concept in SUBSCRIPTION_DEFAULT_CONCEPTS:
                subcategory = (
                    db.query(Category)
                    .filter(Category.nombre == concept, Category.padre_id == subscriptions_parent.id)
                    .first()
                )
                if subcategory is None:
                    subcategory = db.query(Category).filter(Category.nombre == concept).first()
                    if subcategory is None:
                        subcategory = Category(
                            nombre=concept,
                            icono="🏷️",
                            color="#9ca3af",
                            naturaleza="gasto",
                            incluida_en_analisis=True,
                            padre_id=subscriptions_parent.id,
                        )
                        db.add(subcategory)
                        db.flush()
                    else:
                        subcategory.padre_id = subscriptions_parent.id

                recurring = (
                    db.query(RecurringExpense)
                    .filter(RecurringExpense.concepto == concept)
                    .first()
                )
                if recurring is None:
                    recurring = RecurringExpense(
                        concepto=concept,
                        subcategoria_id=subcategory.id,
                        importe=Decimal("0"),
                        tipo="fijo",
                    )
                    db.add(recurring)
                    db.flush()
                    db.add(RecurringExpenseTier(expense_id=recurring.id, importe=Decimal("0"), meses=None))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
