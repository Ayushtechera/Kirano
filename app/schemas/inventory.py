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

    model_config = ConfigDict(from_attributes=True)


