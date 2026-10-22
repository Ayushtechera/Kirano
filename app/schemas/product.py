from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from decimal import Decimal

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    barcode: str = Field(min_length=1, max_length=50)
    category_id: int = Field(gt=0)
    weight: str | None = None
    selling_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    cost_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)



class ProductResponse(BaseModel):
    id: int
    name: str
    barcode: str
    category_id: int
    weight: str | None
    selling_price: Decimal
    cost_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class InventoryBatchResponse(BaseModel):
    id: int
    quantity: int
    expiry_date: date
    stock_added_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductDetailResponse(ProductResponse):
    inventory_batches: list[InventoryBatchResponse] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1,max_length=100)
    weight: str | None = None
    selling_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    cost_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)