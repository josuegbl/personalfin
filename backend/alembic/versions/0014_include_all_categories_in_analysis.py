"""include every category in basic analysis

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO categories (
                nombre,
                icono,
                color,
                es_compartida_por_defecto,
                naturaleza,
                incluida_en_analisis
            )
            SELECT 'Transferencias', '↔️', '#94a3b8', FALSE, 'transferencia', TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM categories WHERE nombre = 'Transferencias'
            )
            """
        )
    )
    op.execute(
        sa.text(
            "UPDATE categories SET incluida_en_analisis = TRUE"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE transactions
            SET categoria_id = NULL
            WHERE categoria_id = (
                SELECT id FROM categories WHERE nombre = 'Transferencias'
            )
            """
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM categories WHERE nombre = 'Transferencias'"
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE categories
            SET incluida_en_analisis = CASE
                WHEN nombre IN ('Sin categoría', 'Transferencias Internas') THEN FALSE
                ELSE TRUE
            END
            """
        )
    )