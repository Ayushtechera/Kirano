from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class StockInCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    expiry_date: date



class StockInResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    expiry_date: date
    stock_added_at: datetime
    status : str
    depleted_at : datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class InventorySummaryResponse(BaseModel):
    product_id : int
    product_name : str
    total_active_quantity : int
    total_active_batches: int
    total_batches: int
    total_quantity_including_expired : int