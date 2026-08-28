"""Add visible_dashboard column to accounts

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("visible_dashboard", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("accounts", "visible_dashboard")
