from pydantic import BaseModel


class CategoryBase(BaseModel):
    nombre: str
    icono: str | None = None
    color: str | None = None
    padre_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryOut(CategoryBase):
    id: int

    model_config = {"from_attributes": True}


class RuleCreate(BaseModel):
    patron: str
    categoria_id: int
    prioridad: int = 0
    es_regex: bool = False


class RuleOut(RuleCreate):
    id: int
    model_config = {"from_attributes": True}
