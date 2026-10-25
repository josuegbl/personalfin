"""add one-time correction flags to monthly balance plan

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monthly_balance_plans",
        sa.Column("gastos_corregidos", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "monthly_balance_plans",
        sa.Column("ingresos_corregidos", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("monthly_balance_plans", "ingresos_corregidos")
    op.drop_column("monthly_balance_plans", "gastos_corregidos")
