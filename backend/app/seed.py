"""
Seed inicial: categorías y gastos estacionales conocidos.
Uso: python -m app.seed
"""
from app.core.database import SessionLocal
from app.models.category import Category
from app.models.recurring_expense import RecurringExpense


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

# Gastos estacionales extraídos del Excel "Pagos A cuenta"
# meses: lista de meses del año en que aplica (1=enero, 12=diciembre)
RECURRING_EXPENSES = [
    # --- Fijos todos los meses ---
    {"concepto": "Hipoteca Caja Rural",      "importe": 550.93, "tipo": "fijo",      "meses": None,                   "dia_cobro": 1,  "categoria": "Vivienda"},
    {"concepto": "Préstamo BBVA JGB",        "importe": 30.30,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 5,  "categoria": "Préstamos"},
    {"concepto": "Kia Stonic",               "importe": 246.04, "tipo": "fijo",      "meses": None,                   "dia_cobro": 5,  "categoria": "Préstamos"},
    {"concepto": "AA Cetelem",               "importe": 124.82, "tipo": "fijo",      "meses": None,                   "dia_cobro": 5,  "categoria": "Préstamos"},
    {"concepto": "Préstamo COFIDIS",         "importe": 238.40, "tipo": "fijo",      "meses": None,                   "dia_cobro": 5,  "categoria": "Préstamos"},
    {"concepto": "Préstamo CETELEM",         "importe": 308.96, "tipo": "fijo",      "meses": None,                   "dia_cobro": 5,  "categoria": "Préstamos"},
    {"concepto": "Inglés Caja Rural",        "importe": 74.22,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 1,  "categoria": "Educación"},
    {"concepto": "Móvil + Internet",         "importe": 109.00, "tipo": "fijo",      "meses": None,                   "dia_cobro": 1,  "categoria": "Vivienda"},
    {"concepto": "Comunidad",                "importe": 80.00,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 1,  "categoria": "Vivienda"},
    {"concepto": "Sanitas Dental",           "importe": 59.90,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 1,  "categoria": "Salud"},
    {"concepto": "Netflix",                  "importe": 14.99,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 15, "categoria": "Suscripciones"},
    {"concepto": "Disney+",                  "importe": 10.99,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 15, "categoria": "Suscripciones"},
    {"concepto": "Max",                      "importe": 7.99,   "tipo": "fijo",      "meses": None,                   "dia_cobro": 15, "categoria": "Suscripciones"},
    {"concepto": "Spotify",                  "importe": 16.99,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 15, "categoria": "Suscripciones"},
    {"concepto": "HP Printer",               "importe": 1.79,   "tipo": "fijo",      "meses": None,                   "dia_cobro": 15, "categoria": "Suscripciones"},
    {"concepto": "Paga Carlos",              "importe": 21.73,  "tipo": "fijo",      "meses": None,                   "dia_cobro": 1,  "categoria": "Otros"},
    # --- Estacionales ---
    {"concepto": "Luz (verano)",             "importe": 150.00, "tipo": "estacional", "meses": [7, 8, 9],             "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Luz (primavera/otoño)",    "importe": 120.00, "tipo": "estacional", "meses": [5, 6, 10, 11],        "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Luz (invierno)",           "importe": 100.00, "tipo": "estacional", "meses": [1, 2, 3, 4, 12],      "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Gas (bimestral)",          "importe": 90.00,  "tipo": "estacional", "meses": [6, 8, 10],            "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Gas (invierno)",           "importe": 130.00, "tipo": "estacional", "meses": [4, 12],               "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Gas (feb)",                "importe": 200.00, "tipo": "estacional", "meses": [2],                   "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Agua (bimestral)",         "importe": 50.00,  "tipo": "estacional", "meses": [1, 3, 5, 7, 9, 11],  "dia_cobro": 15, "categoria": "Vivienda"},
    {"concepto": "Comedor colegio",          "importe": 121.00, "tipo": "estacional", "meses": [2, 3, 4, 5, 6],       "dia_cobro": 1,  "categoria": "Educación"},
    {"concepto": "Comedor colegio (inicio)", "importe": 242.00, "tipo": "estacional", "meses": [10],                  "dia_cobro": 1,  "categoria": "Educación"},
    {"concepto": "Seguro Toyota",            "importe": 471.64, "tipo": "estacional", "meses": [9],                   "dia_cobro": 1,  "categoria": "Seguros"},
    {"concepto": "Seguro Kia",               "importe": 121.82, "tipo": "estacional", "meses": [2, 4],                "dia_cobro": 1,  "categoria": "Seguros"},
    {"concepto": "Seguro Hogar",             "importe": 98.12,  "tipo": "estacional", "meses": [2, 5, 8, 11],         "dia_cobro": 1,  "categoria": "Seguros"},
    {"concepto": "Seguro Vida",              "importe": 121.91, "tipo": "estacional", "meses": [2, 5, 8, 11],         "dia_cobro": 1,  "categoria": "Seguros"},
    {"concepto": "Amazon Prime",             "importe": 49.99,  "tipo": "estacional", "meses": [9],                   "dia_cobro": 1,  "categoria": "Suscripciones"},
    {"concepto": "Microsoft 365",            "importe": 129.99, "tipo": "estacional", "meses": [8],                   "dia_cobro": 1,  "categoria": "Suscripciones"},
    {"concepto": "Mantenimiento caldera",    "importe": 155.05, "tipo": "estacional", "meses": [5],                   "dia_cobro": 1,  "categoria": "Vivienda"},
    {"concepto": "Comisión tarjeta",         "importe": 80.00,  "tipo": "estacional", "meses": [7],                   "dia_cobro": 1,  "categoria": "Otros"},
    {"concepto": "Remesas (meses impares)",  "importe": 100.00, "tipo": "estacional", "meses": [1, 3, 5, 7, 9, 11],  "dia_cobro": 15, "categoria": "Otros"},
    {"concepto": "Remesas (meses pares)",    "importe": 200.00, "tipo": "estacional", "meses": [4, 6, 8, 10, 12],    "dia_cobro": 15, "categoria": "Otros"},
    {"concepto": "Remesas (febrero)",        "importe": 300.00, "tipo": "estacional", "meses": [2],                   "dia_cobro": 15, "categoria": "Otros"},
]


def seed():
    db = SessionLocal()
    try:
        # Categories
        existing = {c.nombre for c in db.query(Category).all()}
        for data in CATEGORIES:
            if data["nombre"] not in existing:
                db.add(Category(**data))
        db.flush()

        # Recurring expenses
        if db.query(RecurringExpense).count() == 0:
            for data in RECURRING_EXPENSES:
                db.add(RecurringExpense(**data))

        db.commit()
        print("Seed completado.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
