from pydantic import BaseModel, ConfigDict


# CategoryCreate → category create karte waqt input validate karega.
# CategoryResponse → response mein kaunse fields (id, name) bhejne hain, define karega.

class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)