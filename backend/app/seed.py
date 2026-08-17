"""
Seed inicial: categorías y gastos estacionales conocidos.
Uso: python -m app.seed
"""
from decimal import Decimal

from app.core.database import SessionLocal
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
    {"nombre": "Nómina",                 "icono": "💰", "color": "#10b981"},
    {"nombre": "Transferencias internas","icono": "↔️", "color": "#94a3b8"},
    {"nombre": "Suscripciones",          "icono": "📱", "color": "#8b5cf6"},
    {"nombre": "PayPal",                 "icono": "💳", "color": "#1d4ed8"},
    {"nombre": "Préstamos",              "icono": "🏦", "color": "#dc2626"},
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
        "concepto": "Préstamo BBVA JGB",
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
        "concepto": "Paga Carlos",
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
                expense_data = {k: v for k, v in data.items() if k != "tiers"}
                expense = RecurringExpense(**expense_data, importe=Decimal("0"))
                db.add(expense)
                db.flush()
                for tier in tiers_data:
                    db.add(RecurringExpenseTier(
                        expense_id=expense.id,
                        importe=Decimal(str(tier["importe"])),
                        meses=tier["meses"],
                    ))

        db.commit()
        print("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
