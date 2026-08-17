"""add recurring_expense_tiers table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recurring_expense_tiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("expense_id", sa.Integer(), nullable=False),
        sa.Column("importe", sa.Numeric(10, 2), nullable=False),
        sa.Column("meses", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.ForeignKeyConstraint(["expense_id"], ["recurring_expenses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recurring_expense_tiers_id", "recurring_expense_tiers", ["id"])

    # Backfill: one tier per existing expense
    op.execute("""
        INSERT INTO recurring_expense_tiers (expense_id, importe, meses)
        SELECT id, importe, meses
        FROM recurring_expenses
        WHERE id NOT IN (SELECT DISTINCT expense_id FROM recurring_expense_tiers)
    """)


def downgrade():
    op.drop_index("ix_recurring_expense_tiers_id", table_name="recurring_expense_tiers")
    op.drop_table("recurring_expense_tiers")
