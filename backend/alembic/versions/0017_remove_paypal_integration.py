"""remove paypal integration

Revision ID: 0017_remove_paypal_integration
Revises: 0016
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0017_remove_paypal_integration"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize existing PayPal values before shrinking enums.
    op.execute("UPDATE accounts SET tipo = 'bank' WHERE tipo::text = 'paypal'")
    op.execute("UPDATE transactions SET origen = 'bank' WHERE origen::text = 'paypal'")

    op.drop_index("ix_transactions_paypal_transaction_id", table_name="transactions")
    op.drop_column("transactions", "paypal_transaction_id")

    op.execute("ALTER TABLE accounts ALTER COLUMN tipo TYPE text USING tipo::text")
    op.execute("DROP TYPE accounttype")
    op.execute("CREATE TYPE accounttype AS ENUM ('bank')")
    op.execute("ALTER TABLE accounts ALTER COLUMN tipo TYPE accounttype USING tipo::accounttype")

    op.execute("ALTER TABLE transactions ALTER COLUMN origen TYPE text USING origen::text")
    op.execute("DROP TYPE transactionorigin")
    op.execute("CREATE TYPE transactionorigin AS ENUM ('bank')")
    op.execute("ALTER TABLE transactions ALTER COLUMN origen TYPE transactionorigin USING origen::transactionorigin")


def downgrade() -> None:
    op.execute("ALTER TABLE accounts ALTER COLUMN tipo TYPE text USING tipo::text")
    op.execute("DROP TYPE accounttype")
    op.execute("CREATE TYPE accounttype AS ENUM ('bank', 'paypal')")
    op.execute("ALTER TABLE accounts ALTER COLUMN tipo TYPE accounttype USING tipo::accounttype")

    op.execute("ALTER TABLE transactions ALTER COLUMN origen TYPE text USING origen::text")
    op.execute("DROP TYPE transactionorigin")
    op.execute("CREATE TYPE transactionorigin AS ENUM ('bank', 'paypal')")
    op.execute("ALTER TABLE transactions ALTER COLUMN origen TYPE transactionorigin USING origen::transactionorigin")

    op.add_column(
        "transactions",
        sa.Column("paypal_transaction_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_transactions_paypal_transaction_id",
        "transactions",
        ["paypal_transaction_id"],
        unique=False,
    )
