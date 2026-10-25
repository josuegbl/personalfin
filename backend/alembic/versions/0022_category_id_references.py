"""recurring_expense and forecast budget category by id

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- recurring_expenses: link legacy rows to their subcategory by name, then drop the string column ---
    op.execute(
        """
        UPDATE recurring_expenses AS re
        SET subcategoria_id = child.id
        FROM categories AS child
        JOIN categories AS parent ON child.padre_id = parent.id
        WHERE re.subcategoria_id IS NULL
          AND re.categoria = parent.nombre
          AND re.concepto = child.nombre
        """
    )
    op.drop_column("recurring_expenses", "categoria")

    # --- forecast_category_budgets: link to categories by id instead of a free-text name ---
    op.add_column("forecast_category_budgets", sa.Column("categoria_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE forecast_category_budgets AS b
        SET categoria_id = c.id
        FROM categories AS c
        WHERE c.nombre = b.categoria_nombre
        """
    )
    op.create_foreign_key(
        "fk_forecast_category_budgets_categoria_id",
        "forecast_category_budgets",
        "categories",
        ["categoria_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_forecast_budget_categoria", "forecast_category_budgets", ["forecast_id", "categoria_id"]
    )
    op.drop_column("forecast_category_budgets", "categoria_nombre")


def downgrade() -> None:
    op.add_column("forecast_category_budgets", sa.Column("categoria_nombre", sa.String(100), nullable=True))
    op.execute(
        """
        UPDATE forecast_category_budgets AS b
        SET categoria_nombre = c.nombre
        FROM categories AS c
        WHERE c.id = b.categoria_id
        """
    )
    op.execute("UPDATE forecast_category_budgets SET categoria_nombre = '' WHERE categoria_nombre IS NULL")
    op.alter_column("forecast_category_budgets", "categoria_nombre", nullable=False)
    op.drop_constraint("uq_forecast_budget_categoria", "forecast_category_budgets", type_="unique")
    op.drop_constraint("fk_forecast_category_budgets_categoria_id", "forecast_category_budgets", type_="foreignkey")
    op.drop_column("forecast_category_budgets", "categoria_id")

    op.add_column("recurring_expenses", sa.Column("categoria", sa.String(100), nullable=True))
    op.execute(
        """
        UPDATE recurring_expenses AS re
        SET categoria = parent.nombre
        FROM categories AS child
        JOIN categories AS parent ON child.padre_id = parent.id
        WHERE re.subcategoria_id = child.id
        """
    )
