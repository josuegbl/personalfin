"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tipo", sa.Enum("bank", "paypal", name="accounttype"), nullable=False),
        sa.Column("proveedor", sa.String(50), nullable=False),
        sa.Column("iban", sa.String(34), nullable=True),
        sa.Column("alias", sa.String(100), nullable=False),
        sa.Column("saldo_actual", sa.Numeric(12, 2), server_default="0.00"),
        sa.Column("moneda", sa.String(3), server_default="EUR"),
        sa.Column("activa", sa.Boolean, server_default="true"),
        sa.Column("ultima_sync", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(100), nullable=False, unique=True),
        sa.Column("icono", sa.String(10), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("padre_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=True),
    )

    op.create_table(
        "categorization_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("patron", sa.String(200), nullable=False),
        sa.Column("categoria_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("prioridad", sa.Integer, server_default="0"),
        sa.Column("es_regex", sa.Boolean, server_default="false"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("importe", sa.Numeric(12, 2), nullable=False),
        sa.Column("concepto_original", sa.Text, nullable=False),
        sa.Column("comercio", sa.String(200), nullable=True),
        sa.Column("categoria_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("subcategoria", sa.String(100), nullable=True),
        sa.Column("recurrente", sa.Boolean, server_default="false"),
        sa.Column("origen", sa.Enum("bank", "paypal", name="transactionorigin"), server_default="bank"),
        sa.Column("paypal_transaction_id", sa.String(100), nullable=True),
        sa.Column("excluir_de_gastos", sa.Boolean, server_default="false"),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("notas", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_fecha", "transactions", ["fecha"])
    op.create_index("ix_transactions_hash", "transactions", ["hash"])
    op.create_index("ix_transactions_paypal_transaction_id", "transactions", ["paypal_transaction_id"])


def downgrade():
    op.drop_table("transactions")
    op.drop_table("categorization_rules")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.execute("DROP TYPE IF EXISTS accounttype")
    op.execute("DROP TYPE IF EXISTS transactionorigin")
