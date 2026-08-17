"""transfer dedup y recurring_expenses

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TYPE transferestado AS ENUM ('completo', 'pendiente')")
    op.add_column(
        "transactions",
        sa.Column("transfer_pair_id", sa.Integer, sa.ForeignKey("transactions.id"), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "transfer_estado",
            sa.Enum("completo", "pendiente", name="transferestado", create_type=False),
            nullable=True,
        ),
    )
    op.create_index("ix_transactions_transfer_pair_id", "transactions", ["transfer_pair_id"])

    op.create_table(
        "recurring_expenses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("concepto", sa.String(200), nullable=False),
        sa.Column("importe", sa.Numeric(10, 2), nullable=False),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("tipo", sa.String(20), server_default="fijo", nullable=False),
        sa.Column("meses", postgresql.ARRAY(sa.Integer), nullable=True),
        sa.Column("dia_cobro", sa.Integer, nullable=True),
        sa.Column("categoria", sa.String(100), nullable=True),
    )


def downgrade():
    op.drop_table("recurring_expenses")
    op.drop_index("ix_transactions_transfer_pair_id", "transactions")
    op.drop_column("transactions", "transfer_estado")
    op.drop_column("transactions", "transfer_pair_id")
    op.execute("DROP TYPE IF EXISTS transferestado")
