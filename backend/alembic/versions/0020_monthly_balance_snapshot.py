"""add monthly balance snapshot tables

Revision ID: 0020
Revises: 0019
"""
from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("monthly_balance_plans"):
        op.create_table(
            "monthly_balance_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("anio", sa.Integer(), nullable=False),
            sa.Column("mes", sa.Integer(), nullable=False),
            sa.Column("ingresos_planificados", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("ingresos_planificados_josue", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("ingresos_planificados_adi", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("cuenta_personal_josue", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.Column("cuenta_personal_adi", sa.Numeric(10, 2), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("anio", "mes", name="uq_monthly_balance_anio_mes"),
        )
        op.create_index("ix_monthly_balance_plans_id", "monthly_balance_plans", ["id"])

    if not inspector.has_table("monthly_balance_category_plans"):
        op.create_table(
            "monthly_balance_category_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("balance_plan_id", sa.Integer(), nullable=False),
            sa.Column("tipo", sa.String(30), nullable=False),
            sa.Column("categoria_nombre", sa.String(100), nullable=False),
            sa.Column("nombre", sa.String(200), nullable=False),
            sa.Column("importe_planificado", sa.Numeric(10, 2), nullable=False),
            sa.ForeignKeyConstraint(["balance_plan_id"], ["monthly_balance_plans.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("balance_plan_id", "tipo", "nombre", name="uq_monthly_balance_category_tipo_nombre"),
        )
        op.create_index("ix_monthly_balance_category_plans_id", "monthly_balance_category_plans", ["id"])

    op.execute(sa.text("""
        INSERT INTO monthly_balance_plans (
            anio,
            mes,
            ingresos_planificados,
            ingresos_planificados_josue,
            ingresos_planificados_adi,
            cuenta_personal_josue,
            cuenta_personal_adi
        )
        SELECT
            fp.anio,
            fp.mes,
            COALESCE(fp.ingresos_planificados, 0),
            COALESCE(fp.ingresos_planificados_josue, 0),
            COALESCE(fp.ingresos_planificados_adi, 0),
            fp.cuenta_personal_josue,
            fp.cuenta_personal_adi
        FROM forecast_plans fp
        WHERE fp.guardado = true
          AND make_date(fp.anio, fp.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
          AND NOT EXISTS (
              SELECT 1
              FROM monthly_balance_plans mbp
              WHERE mbp.anio = fp.anio AND mbp.mes = fp.mes
          )
    """))
    op.execute(sa.text("""
        INSERT INTO monthly_balance_category_plans (
            balance_plan_id,
            tipo,
            categoria_nombre,
            nombre,
            importe_planificado
        )
        SELECT mbp.id, 'ingreso', 'Ingresos', 'Josué', mbp.ingresos_planificados_josue
        FROM monthly_balance_plans mbp
        WHERE NOT EXISTS (
            SELECT 1
            FROM monthly_balance_category_plans line
            WHERE line.balance_plan_id = mbp.id
              AND line.tipo = 'ingreso'
              AND line.nombre = 'Josué'
        )
    """))
    op.execute(sa.text("""
        INSERT INTO monthly_balance_category_plans (
            balance_plan_id,
            tipo,
            categoria_nombre,
            nombre,
            importe_planificado
        )
        SELECT mbp.id, 'ingreso', 'Ingresos', 'Adi', mbp.ingresos_planificados_adi
        FROM monthly_balance_plans mbp
        WHERE NOT EXISTS (
            SELECT 1
            FROM monthly_balance_category_plans line
            WHERE line.balance_plan_id = mbp.id
              AND line.tipo = 'ingreso'
              AND line.nombre = 'Adi'
        )
    """))
    op.execute(sa.text("""
        INSERT INTO monthly_balance_category_plans (
            balance_plan_id,
            tipo,
            categoria_nombre,
            nombre,
            importe_planificado
        )
        SELECT mbp.id, 'asignacion_personal', 'Asignaciones personales', 'Josué', mbp.cuenta_personal_josue
        FROM monthly_balance_plans mbp
        WHERE NOT EXISTS (
            SELECT 1
            FROM monthly_balance_category_plans line
            WHERE line.balance_plan_id = mbp.id
              AND line.tipo = 'asignacion_personal'
              AND line.nombre = 'Josué'
        )
    """))
    op.execute(sa.text("""
        INSERT INTO monthly_balance_category_plans (
            balance_plan_id,
            tipo,
            categoria_nombre,
            nombre,
            importe_planificado
        )
        SELECT mbp.id, 'asignacion_personal', 'Asignaciones personales', 'Adi', mbp.cuenta_personal_adi
        FROM monthly_balance_plans mbp
        WHERE NOT EXISTS (
            SELECT 1
            FROM monthly_balance_category_plans line
            WHERE line.balance_plan_id = mbp.id
              AND line.tipo = 'asignacion_personal'
              AND line.nombre = 'Adi'
        )
    """))
    op.execute(sa.text("""
        INSERT INTO monthly_balance_category_plans (
            balance_plan_id,
            tipo,
            categoria_nombre,
            nombre,
            importe_planificado
        )
        SELECT
            mbp.id,
            'gasto_variable',
            fcb.categoria_nombre,
            fcb.categoria_nombre,
            fcb.importe_planificado
        FROM forecast_category_budgets fcb
        JOIN forecast_plans fp ON fp.id = fcb.forecast_id
        JOIN monthly_balance_plans mbp ON mbp.anio = fp.anio AND mbp.mes = fp.mes
        WHERE fp.guardado = true
          AND make_date(fp.anio, fp.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
          AND NOT EXISTS (
              SELECT 1
              FROM monthly_balance_category_plans line
              WHERE line.balance_plan_id = mbp.id
                AND line.tipo = 'gasto_variable'
                AND line.nombre = fcb.categoria_nombre
          )
    """))


def downgrade() -> None:
    op.drop_index("ix_monthly_balance_category_plans_id", table_name="monthly_balance_category_plans")
    op.drop_table("monthly_balance_category_plans")
    op.drop_index("ix_monthly_balance_plans_id", table_name="monthly_balance_plans")
    op.drop_table("monthly_balance_plans")
