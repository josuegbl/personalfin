"""remove legacy transfer and exclusion fields

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "transactions_transfer_pair_id_fkey",
        "transactions",
        type_="foreignkey",
    )
    op.drop_index("ix_transactions_transfer_pair_id", table_name="transactions")
    op.drop_column("transactions", "transfer_pair_id")
    op.drop_column("transactions", "transfer_estado")
    op.drop_column("transactions", "excluir_de_gastos")
    op.execute("DROP TYPE IF EXISTS transferestado")


def downgrade() -> None:
    op.execute("CREATE TYPE transferestado AS ENUM ('completo', 'pendiente')")
    op.add_column(
        "transactions",
        sa.Column("excluir_de_gastos", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "transfer_estado",
            sa.Enum("completo", "pendiente", name="transferestado", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "transfer_pair_id",
            sa.Integer,
            sa.ForeignKey("transactions.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_transactions_transfer_pair_id", "transactions", ["transfer_pair_id"])