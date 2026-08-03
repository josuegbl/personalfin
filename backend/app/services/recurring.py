from collections import defaultdict
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from app.models.transaction import Transaction


RECURRENT_KEYWORDS = [
    "HIPOTECA", "LUZ", "AGUA", "GAS ", "INTERNET", "SEGURO",
    "NETFLIX", "SPOTIFY", "AMAZON PRIME", "COLEGIO", "GUARDERÍA",
    "VODAFONE", "MOVISTAR", "ORANGE", "COMUNIDAD",
]


def detect_recurring(db: Session):
    """
    Marca como recurrente cualquier transacción cuyo comercio aparece
    al menos 2 veces en los últimos 3 meses.
    """
    today = date.today()

    rows = (
        db.query(
            Transaction.comercio,
            func.count(Transaction.id).label("cnt"),
        )
        .filter(
            Transaction.fecha >= date(today.year, today.month, 1).replace(month=max(1, today.month - 2)),
            Transaction.comercio != None,
        )
        .group_by(Transaction.comercio)
        .having(func.count(Transaction.id) >= 2)
        .all()
    )

    recurring_comercios = {r.comercio for r in rows}

    updated = 0
    candidates = (
        db.query(Transaction)
        .filter(Transaction.recurrente == False, Transaction.comercio != None)
        .all()
    )

    for t in candidates:
        is_keyword = any(kw in (t.concepto_original or "").upper() for kw in RECURRENT_KEYWORDS)
        is_frequent = t.comercio in recurring_comercios
        if is_keyword or is_frequent:
            t.recurrente = True
            updated += 1

    db.commit()
    return updated
