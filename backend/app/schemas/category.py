from pydantic import BaseModel


class CategoryBase(BaseModel):
    nombre: str
    icono: str | None = None
    color: str | None = None
    padre_id: int | None = None
    naturaleza: str = "gasto"
    incluida_en_analisis: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    nombre: str


class CategoryOut(CategoryBase):
    id: int
    se_puede_eliminar: bool = False

    model_config = {"from_attributes": True}
