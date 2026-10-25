FIXED_CATEGORY_NAMES: list[str] = [
    "Vivienda",
    "Seguros",
    "Préstamos",
    "Suscripciones",
    "Tarjeta Credito",
    "Remesas",
    "Impuestos",
    "Deportes",
]

SUBSCRIPTION_DEFAULT_CONCEPTS: list[str] = [
    "Netflix",
    "Amazon Prime",
    "Disney+",
    "HBO Max",
    "Spotify",
    "HP Printer",
    "Microsoft 365",
]

_CATEGORY_ALIASES: dict[str, str] = {
    "prestamos": "Préstamos",
    "préstamos": "Préstamos",
    "tarjetas de credito": "Tarjeta Credito",
    "tarjetas de crédito": "Tarjeta Credito",
    "tarjeta de credito": "Tarjeta Credito",
    "tarjeta de crédito": "Tarjeta Credito",
}


def normalize_fixed_category_name(name: str) -> str:
    """Map category aliases to canonical fixed-category names."""
    stripped = name.strip()
    if not stripped:
        return stripped
    return _CATEGORY_ALIASES.get(stripped.lower(), stripped)
