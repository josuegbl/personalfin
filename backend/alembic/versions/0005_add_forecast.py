"""add forecast_plans and forecast_category_budgets tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "forecast_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.Column("ingresos_josue", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("ingresos_adi", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("ingresos_extra", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("anio", "mes", name="uq_forecast_anio_mes"),
    )
    op.create_index("ix_forecast_plans_id", "forecast_plans", ["id"])

    op.create_table(
        "forecast_category_budgets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("forecast_id", sa.Integer(), nullable=False),
        sa.Column("categoria_nombre", sa.String(100), nullable=False),
        sa.Column("importe_planificado", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["forecast_id"], ["forecast_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_category_budgets_id", "forecast_category_budgets", ["id"])


def downgrade():
    op.drop_index("ix_forecast_category_budgets_id", table_name="forecast_category_budgets")
    op.drop_table("forecast_category_budgets")
    op.drop_index("ix_forecast_plans_id", table_name="forecast_plans")
    op.drop_table("forecast_plans")
