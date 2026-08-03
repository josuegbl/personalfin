import re
from sqlalchemy.orm import Session
from app.models.category import Category, CategorizationRule
from app.models.transaction import Transaction


def categorize_transaction(t: Transaction, db: Session) -> int | None:
    """Aplica las reglas de categorización por orden de prioridad."""
    rules = (
        db.query(CategorizationRule)
        .order_by(CategorizationRule.prioridad.desc())
        .all()
    )

    texto = f"{t.concepto_original} {t.comercio or ''}".upper()

    for rule in rules:
        if rule.es_regex:
            if re.search(rule.patron, texto, re.IGNORECASE):
                return rule.categoria_id
        else:
            if rule.patron.upper() in texto:
                return rule.categoria_id

    return None


def auto_categorize_pending(db: Session):
    """Categoriza en lote todas las transacciones sin categoría."""
    pending = db.query(Transaction).filter(Transaction.categoria_id == None).all()
    updated = 0
    for t in pending:
        cat_id = categorize_transaction(t, db)
        if cat_id:
            t.categoria_id = cat_id
            updated += 1
    db.commit()
    return updated


def mark_paypal_passthroughs(db: Session):
    """
    Marca como excluir_de_gastos=True los movimientos bancarios que son
    traspasos hacia PayPal, para evitar el doble cómputo.
    """
    paypal_cat = db.query(Category).filter(Category.nombre == "PayPal").first()
    if not paypal_cat:
        return 0

    passthroughs = (
        db.query(Transaction)
        .filter(
            Transaction.categoria_id == paypal_cat.id,
            Transaction.origen == "bank",
            Transaction.excluir_de_gastos == False,
        )
        .all()
    )
    for t in passthroughs:
        t.excluir_de_gastos = True
    db.commit()
    return len(passthroughs)
