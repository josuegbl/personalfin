"""Earliest month with meaningful forecast/dashboard data."""

MIN_ANIO = 2026
MIN_MES = 1


def is_before_min_month(anio: int, mes: int) -> bool:
    """Return True if (anio, mes) is earlier than the app's minimum supported month."""
    return (anio, mes) < (MIN_ANIO, MIN_MES)
