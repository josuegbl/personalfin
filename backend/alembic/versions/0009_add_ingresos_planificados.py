"""add ingresos_planificados to forecast_plans

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_plans",
        sa.Column("ingresos_planificados", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("forecast_plans", "ingresos_planificados")
