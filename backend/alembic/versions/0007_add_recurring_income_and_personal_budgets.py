"""Add recurring_incomes table and personal budget columns to forecast_plans

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Table may already exist if create_all ran before this migration
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS recurring_incomes (
            id SERIAL NOT NULL PRIMARY KEY,
            concepto VARCHAR(200) NOT NULL,
            importe NUMERIC(10, 2) NOT NULL,
            propietario VARCHAR(100),
            activa BOOLEAN NOT NULL DEFAULT true,
            orden INTEGER NOT NULL DEFAULT 0
        )
    """))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_recurring_incomes_id ON recurring_incomes (id)"
    ))

    conn.execute(sa.text("""
        ALTER TABLE forecast_plans
            ADD COLUMN IF NOT EXISTS cuenta_personal_josue NUMERIC(10, 2) NOT NULL DEFAULT 0
    """))
    conn.execute(sa.text("""
        ALTER TABLE forecast_plans
            ADD COLUMN IF NOT EXISTS cuenta_personal_adi NUMERIC(10, 2) NOT NULL DEFAULT 0
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE forecast_plans DROP COLUMN IF EXISTS cuenta_personal_adi"))
    conn.execute(sa.text("ALTER TABLE forecast_plans DROP COLUMN IF EXISTS cuenta_personal_josue"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_recurring_incomes_id"))
    conn.execute(sa.text("DROP TABLE IF EXISTS recurring_incomes"))
