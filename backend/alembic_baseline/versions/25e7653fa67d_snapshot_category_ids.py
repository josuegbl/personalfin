"""snapshot category IDs

Revision ID: 25e7653fa67d
Revises: bcd5f4f582de
Create Date: 2026-10-25 11:10:28.350560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25e7653fa67d'
down_revision: Union[str, None] = 'bcd5f4f582de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monthly_balance_category_plans
                WHERE tipo IN ('gasto_fijo', 'gasto_variable')
                  AND categoria_id IS NULL
            ) THEN
                RAISE EXCEPTION 'Cannot drop category labels while expense snapshot lines have NULL categoria_id';
            END IF;
        END;
        $$;
    """))
    op.alter_column('monthly_balance_category_plans', 'nombre',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    op.execute(
        "UPDATE monthly_balance_category_plans SET nombre = NULL WHERE tipo = 'gasto_variable'"
    )
    op.create_index('uq_monthly_balance_variable_categoria', 'monthly_balance_category_plans', ['balance_plan_id', 'categoria_id'], unique=True, postgresql_where=sa.text("tipo = 'gasto_variable'"))
    op.drop_column('monthly_balance_category_plans', 'categoria_nombre')


def downgrade() -> None:
    op.add_column(
        'monthly_balance_category_plans',
        sa.Column('categoria_nombre', sa.VARCHAR(length=100), nullable=True),
    )
    op.execute(sa.text("""
        UPDATE monthly_balance_category_plans AS line
        SET categoria_nombre = CASE
            WHEN line.tipo = 'ingreso' THEN 'Ingresos'
            WHEN line.tipo = 'asignacion_personal' THEN 'Asignaciones personales'
            ELSE COALESCE(parent.nombre, category.nombre, 'Sin categoría')
        END
        FROM categories AS category
        LEFT JOIN categories AS parent ON parent.id = category.padre_id
        WHERE line.categoria_id = category.id
    """))
    op.execute(sa.text("""
        UPDATE monthly_balance_category_plans
        SET categoria_nombre = 'Ingresos'
        WHERE tipo = 'ingreso' AND categoria_nombre IS NULL
    """))
    op.execute(sa.text("""
        UPDATE monthly_balance_category_plans
        SET categoria_nombre = 'Asignaciones personales'
        WHERE tipo = 'asignacion_personal' AND categoria_nombre IS NULL
    """))
    op.execute(sa.text("""
        UPDATE monthly_balance_category_plans AS line
        SET nombre = category.nombre
        FROM categories AS category
        WHERE line.tipo = 'gasto_variable'
          AND line.categoria_id = category.id
          AND line.nombre IS NULL
    """))
    op.alter_column(
        'monthly_balance_category_plans',
        'nombre',
        existing_type=sa.VARCHAR(length=200),
        nullable=False,
    )
    op.alter_column(
        'monthly_balance_category_plans',
        'categoria_nombre',
        existing_type=sa.VARCHAR(length=100),
        nullable=False,
    )
    op.drop_index('uq_monthly_balance_variable_categoria', table_name='monthly_balance_category_plans', postgresql_where=sa.text("tipo = 'gasto_variable'"))
