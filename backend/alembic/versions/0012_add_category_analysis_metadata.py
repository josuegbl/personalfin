"""add category analysis metadata

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("naturaleza", sa.String(20), nullable=False, server_default="gasto"),
    )
    op.add_column(
        "categories",
        sa.Column("incluida_en_analisis", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.execute(
        sa.text(
            """
            UPDATE categories
            SET naturaleza = CASE
                WHEN nombre = 'Nómina' THEN 'ingreso'
                WHEN nombre = 'Transferencias Internas' THEN 'transferencia'
                WHEN nombre = 'Sin categoría' THEN 'neutral'
                ELSE 'gasto'
            END,
            incluida_en_analisis = CASE
                WHEN nombre IN ('Transferencias Internas', 'Sin categoría') THEN false
                ELSE true
            END
            """
        )
    )


def downgrade() -> None:
    op.drop_column("categories", "incluida_en_analisis")
    op.drop_column("categories", "naturaleza")