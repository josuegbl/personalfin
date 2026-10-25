"""add validity dates to recurring expenses

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recurring_expenses", sa.Column("vigente_desde", sa.Date(), nullable=True))
    op.add_column("recurring_expenses", sa.Column("vigente_hasta", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("recurring_expenses", "vigente_hasta")
    op.drop_column("recurring_expenses", "vigente_desde")