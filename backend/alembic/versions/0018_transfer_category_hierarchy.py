"""add transfer category hierarchy

Revision ID: 0018
Revises: 0017_remove_paypal_integration
Create Date: 2026-08-19
"""

from alembic import op


revision = "0018"
down_revision = "0017_remove_paypal_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO categories (
            nombre, color, es_compartida_por_defecto, naturaleza, incluida_en_analisis
        )
        VALUES ('Transferencias', '#a3a3a3', FALSE, 'transferencia', TRUE)
        ON CONFLICT (nombre) DO UPDATE
        SET naturaleza = EXCLUDED.naturaleza,
            incluida_en_analisis = EXCLUDED.incluida_en_analisis
        """
    )
    op.execute(
        """
        INSERT INTO categories (
            nombre, color, padre_id, es_compartida_por_defecto, naturaleza, incluida_en_analisis
        )
        SELECT item.nombre, '#a3a3a3', parent.id, FALSE, item.naturaleza, item.incluida_en_analisis
        FROM categories AS parent
        CROSS JOIN (
            VALUES
                ('Entrantes', 'ingreso', TRUE),
                ('Salientes', 'gasto', TRUE),
                ('Internas', 'neutral', FALSE)
        ) AS item(nombre, naturaleza, incluida_en_analisis)
        WHERE parent.nombre = 'Transferencias'
        ON CONFLICT (nombre) DO UPDATE
        SET padre_id = EXCLUDED.padre_id,
            naturaleza = EXCLUDED.naturaleza,
            incluida_en_analisis = EXCLUDED.incluida_en_analisis
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET categoria_id = (SELECT id FROM categories WHERE nombre = 'Internas')
        WHERE categoria_id = (SELECT id FROM categories WHERE nombre = 'Transferencias Internas')
        """
    )
    op.execute(
        """
        UPDATE recurring_expenses
        SET subcategoria_id = (SELECT id FROM categories WHERE nombre = 'Internas')
        WHERE subcategoria_id = (SELECT id FROM categories WHERE nombre = 'Transferencias Internas')
        """
    )
    op.execute("DELETE FROM categories WHERE nombre = 'Transferencias Internas'")


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO categories (
            nombre, color, es_compartida_por_defecto, naturaleza, incluida_en_analisis
        )
        VALUES ('Transferencias Internas', '#a3a3a3', FALSE, 'transferencia', TRUE)
        ON CONFLICT (nombre) DO NOTHING
        """
    )