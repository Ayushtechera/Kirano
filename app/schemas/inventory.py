from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

class StockInCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    expiry_date: date
    unit_cost: Decimal = Field(gt=0)



class StockInResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    expiry_date: date
    stock_added_at: datetime
    status : str
    depleted_at : datetime | None = None
    unit_cost: Decimal | None = None
    model_config = ConfigDict(from_attributes=True)


class InventorySummaryResponse(BaseModel):
    product_id : int
    product_name : str
    total_active_quantity : int
    total_active_batches: int
    total_batches: int
    total_quantity_including_expired : int


class InventoryValuationResponse(BaseModel):
    active_stock_value: Decimal
    expired_stock_loss: Decimal
    active_unknown_cost_quantity: int
    expired_unknown_cost_quantity: int

class NearExpiryResponse(BaseModel):
    product_id: int
    product_name: str
    batch_id: int
    quantity: int
    expiry_date: date
    days_until_expiry: int