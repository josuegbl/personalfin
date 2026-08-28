"""neutralize forecast owner column names

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _rename_if_present(connection: sa.Connection, old_parts: tuple[str, ...], new_name: str) -> None:
    old_name = "".join(old_parts)
    result = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'forecast_plans' AND column_name = :column_name"
        ),
        {"column_name": old_name},
    ).first()
    if result:
        connection.execute(
            sa.text("ALTER TABLE forecast_plans RENAME COLUMN " + old_name + " TO " + new_name)
        )


def upgrade() -> None:
    connection = op.get_bind()
    renames = (
        (("ingresos_", "jos", "ue"), "ingresos_persona_a"),
        (("ingresos_", "a", "di"), "ingresos_persona_b"),
        (("cuenta_personal_", "jos", "ue"), "cuenta_personal_a"),
        (("cuenta_personal_", "a", "di"), "cuenta_personal_b"),
        (("ingresos_planificados_", "jos", "ue"), "ingresos_planificados_a"),
        (("ingresos_planificados_", "a", "di"), "ingresos_planificados_b"),
    )
    for old_parts, new_name in renames:
        _rename_if_present(connection, old_parts, new_name)


def downgrade() -> None:
    connection = op.get_bind()
    renames = (
        (("ingresos_persona_a",), ("ingresos_", "jos", "ue")),
        (("ingresos_persona_b",), ("ingresos_", "a", "di")),
        (("cuenta_personal_a",), ("cuenta_personal_", "jos", "ue")),
        (("cuenta_personal_b",), ("cuenta_personal_", "a", "di")),
        (("ingresos_planificados_a",), ("ingresos_planificados_", "jos", "ue")),
        (("ingresos_planificados_b",), ("ingresos_planificados_", "a", "di")),
    )
    for old_parts, new_parts in renames:
        _rename_if_present(connection, old_parts, "".join(new_parts))
