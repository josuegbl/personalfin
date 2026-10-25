"""Canonical category allowlist.

This is the single source of truth for category names. Update this list before
adding, renaming, or removing a category in the application or database.
"""

from typing import Final


# Keep this list synchronized with the categories that are intentionally
# present in the database. The parent name is None for top-level categories.
CANONICAL_CATEGORIES: Final[tuple[tuple[str, str | None], ...]] = (
    ("Agua", "Vivienda"),
    ("Comunidad", "Vivienda"),
    ("Gas", "Vivienda"),
    ("Hipoteca", "Vivienda"),
    ("Internet", "Vivienda"),
    ("Luz", "Vivienda"),
    ("Mantenimiento caldera", "Vivienda"),
    ("Movil Adi", "Vivienda"),
    ("Gasolina", "Transporte"),
    ("Limpieza Coche", "Transporte"),
    ("Parking", "Transporte"),
    ("Peajes", "Transporte"),
    ("Transporte Público", "Transporte"),
    ("Farmacias", "Salud"),
    ("Sanitas Dental", "Salud"),
    ("Clases Particulares Ingles", "Educación"),
    ("Comedor Colegio", "Educación"),
    ("Seguro Hogar", "Seguros"),
    ("Seguro Kia", "Seguros"),
    ("Seguro Toyota", "Seguros"),
    ("Seguro Vida", "Seguros"),
    ("Amazon Prime", "Suscripciones"),
    ("Apple", "Suscripciones"),
    ("Disney+", "Suscripciones"),
    ("HBO Max", "Suscripciones"),
    ("HP Printer", "Suscripciones"),
    ("Microsoft 365", "Suscripciones"),
    ("Netflix", "Suscripciones"),
    ("Spotify", "Suscripciones"),
    ("Abonos varios", "Otros"),
    ("Comisiones", "Otros"),
    ("Comisión tarjeta", "Otros"),
    ("Lotería", "Otros"),
    ("Paga Carlos", "Otros"),
    ("Entrantes", "Transferencias"),
    ("Internas", "Transferencias"),
    ("Salientes", "Transferencias"),
    ("AA Cetelem", "Préstamos"),
    ("BBVA JGB", "Préstamos"),
    ("CETELEM", "Préstamos"),
    ("COFIDIS", "Préstamos"),
    ("Kia Stonic", "Préstamos"),
    ("Oney Ventanas", "Préstamos"),
    ("T. Credito Adi", "Tarjeta Credito"),
    ("T. Credito Josue", "Tarjeta Credito"),
    ("Alimentación", None),
    ("Cajeros", None),
    ("Compras", None),
    ("Devoluciones", None),
    ("Deportes", None),
    ("Educación", None),
    ("Impuestos", None),
    ("Nómina", None),
    ("Ocio", None),
    ("Otros", None),
    ("Préstamos", None),
    ("Remesas", None),
    ("Restaurantes", None),
    ("Salud", None),
    ("Seguros", None),
    ("Sin categoría", None),
    ("Supermercado", None),
    ("Suscripciones", None),
    ("Tarjeta Credito", None),
    ("Transferencias", None),
    ("Transporte", None),
    ("Vivienda", None),
)

CANONICAL_CATEGORY_NAMES: Final[frozenset[str]] = frozenset(
    name for name, _parent in CANONICAL_CATEGORIES
)

CANONICAL_CATEGORY_PARENTS: Final[dict[str, str | None]] = dict(CANONICAL_CATEGORIES)

SIGN_BASED_CATEGORY_NAMES: Final[frozenset[str]] = frozenset({"Impuestos"})

# Stable identifiers for categories whose business meaning is load-bearing
# (salary detection, default uncategorized bucket). Independent of `nombre`,
# which is user-editable. See Category.codigo_sistema.
CATEGORY_CODE_NOMINA: Final[str] = "nomina"
CATEGORY_CODE_SIN_CATEGORIA: Final[str] = "sin_categoria"
