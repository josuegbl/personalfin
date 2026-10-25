"""add category codigo_sistema

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("codigo_sistema", sa.String(50), nullable=True))
    op.create_unique_constraint("uq_categories_codigo_sistema", "categories", ["codigo_sistema"])
    op.execute("UPDATE categories SET codigo_sistema = 'nomina' WHERE nombre = 'Nómina'")
    op.execute("UPDATE categories SET codigo_sistema = 'sin_categoria' WHERE nombre = 'Sin categoría'")


def downgrade() -> None:
    op.drop_constraint("uq_categories_codigo_sistema", "categories", type_="unique")
    op.drop_column("categories", "codigo_sistema")
