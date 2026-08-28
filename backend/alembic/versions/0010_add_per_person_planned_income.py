"""add per-person planned income and guardado to forecast_plans

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "forecast_plans",
        sa.Column("ingresos_planificados_a", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "forecast_plans",
        sa.Column("ingresos_planificados_b", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "forecast_plans",
        sa.Column("guardado", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("forecast_plans", "guardado")
    op.drop_column("forecast_plans", "ingresos_planificados_b")
    op.drop_column("forecast_plans", "ingresos_planificados_a")
