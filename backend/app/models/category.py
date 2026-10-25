from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("codigo_sistema", name="uq_categories_codigo_sistema"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icono: Mapped[str | None] = mapped_column(String(10), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex color
    padre_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    es_compartida_por_defecto: Mapped[bool] = mapped_column(default=False)
    naturaleza: Mapped[str] = mapped_column(String(20), default="gasto")
    incluida_en_analisis: Mapped[bool] = mapped_column(default=True)
    codigo_sistema: Mapped[str | None] = mapped_column(String(50), nullable=True)

    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side=[id],
        back_populates="subcategorias",
    )
    subcategorias: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
    )
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="categoria")
