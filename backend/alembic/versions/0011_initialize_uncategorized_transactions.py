"""initialize all transactions as uncategorized

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-19
"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    categories = sa.table(
        "categories",
        sa.column("id", sa.Integer),
        sa.column("nombre", sa.String),
        sa.column("icono", sa.String),
        sa.column("color", sa.String),
        sa.column("es_compartida_por_defecto", sa.Boolean),
    )
    transactions = sa.table(
        "transactions",
        sa.column("categoria_id", sa.Integer),
    )

    op.execute(
        sa.text(
            """
            UPDATE categories
            SET nombre = 'Transferencias Internas'
            WHERE nombre = 'Transferencias internas'
              AND NOT EXISTS (
                  SELECT 1 FROM categories WHERE nombre = 'Transferencias Internas'
              )
            """
        )
    )
    op.execute(
        categories.insert().from_select(
            ["nombre", "icono", "color", "es_compartida_por_defecto"],
            sa.select(
                sa.literal("Transferencias Internas"),
                sa.literal("↔️"),
                sa.literal("#a3a3a3"),
                sa.literal(False),
            ).where(
                ~sa.exists(
                    sa.select(categories.c.id).where(
                        categories.c.nombre == "Transferencias Internas"
                    )
                )
            ),
        )
    )
    op.execute(
        categories.insert().from_select(
            ["nombre", "icono", "color", "es_compartida_por_defecto"],
            sa.select(
                sa.literal("Sin categoría"),
                sa.literal("?"),
                sa.literal("#94a3b8"),
                sa.literal(False),
            ).where(
                ~sa.exists(
                    sa.select(categories.c.id).where(
                        categories.c.nombre == "Sin categoría"
                    )
                )
            ),
        )
    )
    op.execute(
        transactions.update().values(
            categoria_id=sa.select(categories.c.id)
            .where(categories.c.nombre == "Sin categoría")
            .scalar_subquery()
        )
    )


def downgrade() -> None:
    categories = sa.table("categories", sa.column("id", sa.Integer), sa.column("nombre", sa.String))
    transactions = sa.table("transactions", sa.column("categoria_id", sa.Integer))
    op.execute(
        transactions.update().where(
            transactions.c.categoria_id == sa.select(categories.c.id)
            .where(categories.c.nombre == "Sin categoría")
            .scalar_subquery()
        ).values(categoria_id=None)
    )
    op.execute(categories.delete().where(categories.c.nombre == "Sin categoría"))