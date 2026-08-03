from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icono: Mapped[str | None] = mapped_column(String(10), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # hex color
    padre_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    es_compartida_por_defecto: Mapped[bool] = mapped_column(default=False)

    subcategorias: Mapped[list["Category"]] = relationship("Category")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="categoria")
    reglas: Mapped[list["CategorizationRule"]] = relationship(back_populates="categoria")


class CategorizationRule(Base):
    __tablename__ = "categorization_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patron: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, default=0)
    es_regex: Mapped[bool] = mapped_column(default=False)

    categoria: Mapped["Category"] = relationship(back_populates="reglas")
