"""add sync_error to accounts

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("sync_error", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("accounts", "sync_error")
