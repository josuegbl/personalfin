"""gastos compartidos y propietario de cuenta

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("propietario", sa.String(100), nullable=True))
    op.add_column("categories", sa.Column("es_compartida_por_defecto", sa.Boolean, server_default="false", nullable=False))
    op.add_column("transactions", sa.Column("es_compartido", sa.Boolean, server_default="false", nullable=False))


def downgrade():
    op.drop_column("transactions", "es_compartido")
    op.drop_column("categories", "es_compartida_por_defecto")
    op.drop_column("accounts", "propietario")
