"""link recurring expenses to category hierarchy and seed fixed catalog

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-19
"""

from __future__ import annotations

from decimal import Decimal

from alembic import context, op
import sqlalchemy as sa


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


FIXED_CATEGORY_NAMES = [
    "Vivienda",
    "Seguros",
    "Préstamos",
    "Suscripciones",
    "Tarjeta Credito",
    "Remesas",
    "Impuestos",
    "Colegios",
    "Deportes",
]

SUBSCRIPTION_DEFAULT_CONCEPTS = [
    "Netflix",
    "Amazon",
    "Disney",
    "HBO",
    "Spotify",
    "HP Printer",
    "Office",
]

ALIASES = {
    "prestamos": "Préstamos",
    "préstamos": "Préstamos",
    "tarjetas de credito": "Tarjeta Credito",
    "tarjetas de crédito": "Tarjeta Credito",
    "tarjeta de credito": "Tarjeta Credito",
    "tarjeta de crédito": "Tarjeta Credito",
    "colegio": "Colegios",
}


def _normalize(name: str | None) -> str:
    if not name:
        return "Otros"
    stripped = name.strip()
    return ALIASES.get(stripped.lower(), stripped)


def _query_scalar(conn, sql: str, **params):
    return conn.execute(sa.text(sql), params).scalar()


def _execute(conn, sql: str, **params) -> None:
    conn.execute(sa.text(sql), params)


def _get_or_create_parent(conn, name: str) -> int:
    category_id = _query_scalar(
        conn,
        "SELECT id FROM categories WHERE nombre = :nombre LIMIT 1",
        nombre=name,
    )
    if category_id:
        _execute(
            conn,
            "UPDATE categories SET padre_id = NULL WHERE id = :id",
            id=category_id,
        )
        return int(category_id)

    category_id = _query_scalar(
        conn,
        """
        INSERT INTO categories (
            nombre,
            icono,
            color,
            es_compartida_por_defecto,
            naturaleza,
            incluida_en_analisis,
            padre_id
        )
        VALUES (:nombre, '📁', '#6b7280', FALSE, 'gasto', TRUE, NULL)
        RETURNING id
        """,
        nombre=name,
    )
    return int(category_id)


def _get_or_create_subcategory(conn, parent_id: int, concept_name: str) -> int:
    existing_id = _query_scalar(
        conn,
        "SELECT id FROM categories WHERE nombre = :nombre AND padre_id = :padre_id LIMIT 1",
        nombre=concept_name,
        padre_id=parent_id,
    )
    if existing_id:
        return int(existing_id)

    # categories.nombre is globally unique in this schema. Reuse the name if already present.
    existing_global_id = _query_scalar(
        conn,
        "SELECT id FROM categories WHERE nombre = :nombre LIMIT 1",
        nombre=concept_name,
    )
    if existing_global_id:
        _execute(
            conn,
            "UPDATE categories SET padre_id = :padre_id WHERE id = :id",
            padre_id=parent_id,
            id=existing_global_id,
        )
        return int(existing_global_id)

    inserted_id = _query_scalar(
        conn,
        """
        INSERT INTO categories (
            nombre,
            icono,
            color,
            es_compartida_por_defecto,
            naturaleza,
            incluida_en_analisis,
            padre_id
        )
        VALUES (:nombre, '🏷️', '#9ca3af', FALSE, 'gasto', TRUE, :padre_id)
        RETURNING id
        """,
        nombre=concept_name,
        padre_id=parent_id,
    )
    return int(inserted_id)


def _ensure_recurring_entry(conn, parent_name: str, concept_name: str) -> None:
    existing_expense_id = _query_scalar(
        conn,
        """
        SELECT id
        FROM recurring_expenses
        WHERE lower(concepto) = lower(:concepto)
          AND (categoria = :categoria OR categoria IS NULL)
        LIMIT 1
        """,
        concepto=concept_name,
        categoria=parent_name,
    )
    if existing_expense_id:
        return

    parent_id = _get_or_create_parent(conn, parent_name)
    subcategory_id = _get_or_create_subcategory(conn, parent_id, concept_name)

    expense_id = _query_scalar(
        conn,
        """
        INSERT INTO recurring_expenses (
            concepto,
            importe,
            account_id,
            tipo,
            meses,
            dia_cobro,
            categoria,
            subcategoria_id
        )
        VALUES (:concepto, :importe, NULL, 'fijo', NULL, NULL, :categoria, :subcategoria_id)
        RETURNING id
        """,
        concepto=concept_name,
        importe=Decimal("0"),
        categoria=parent_name,
        subcategoria_id=subcategory_id,
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO recurring_expense_tiers (expense_id, importe, meses)
            VALUES (:expense_id, :importe, NULL)
            """
        ),
        {"expense_id": expense_id, "importe": Decimal("0")},
    )


def upgrade() -> None:
    op.add_column("recurring_expenses", sa.Column("subcategoria_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_recurring_expenses_subcategoria_id",
        "recurring_expenses",
        "categories",
        ["subcategoria_id"],
        ["id"],
    )
    op.create_index(
        "ix_recurring_expenses_subcategoria_id",
        "recurring_expenses",
        ["subcategoria_id"],
    )

    if context.is_offline_mode():
        return
    conn = op.get_bind()

    for name in FIXED_CATEGORY_NAMES:
        _get_or_create_parent(conn, name)

    rows = conn.execute(
        sa.text("SELECT id, concepto, categoria FROM recurring_expenses")
    ).fetchall()
    for row in rows:
        parent_name = _normalize(row.categoria)
        concept_name = (row.concepto or "").strip()
        if not concept_name:
            continue
        parent_id = _get_or_create_parent(conn, parent_name)
        subcategory_id = _get_or_create_subcategory(conn, parent_id, concept_name)
        conn.execute(
            sa.text(
                """
                UPDATE recurring_expenses
                SET categoria = :categoria,
                    subcategoria_id = :subcategoria_id,
                    concepto = :concepto
                WHERE id = :expense_id
                """
            ),
            {
                "categoria": parent_name,
                "subcategoria_id": subcategory_id,
                "concepto": concept_name,
                "expense_id": row.id,
            },
        )

    for concept_name in SUBSCRIPTION_DEFAULT_CONCEPTS:
        _ensure_recurring_entry(conn, "Suscripciones", concept_name)


def downgrade() -> None:
    op.drop_index("ix_recurring_expenses_subcategoria_id", table_name="recurring_expenses")
    op.drop_constraint("fk_recurring_expenses_subcategoria_id", "recurring_expenses", type_="foreignkey")
    op.drop_column("recurring_expenses", "subcategoria_id")
