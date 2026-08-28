"""remove unused automatic categorization rules

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-19
"""

from alembic import op


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("categorization_rules")


def downgrade() -> None:
    raise RuntimeError("Automatic categorization rules were intentionally removed")