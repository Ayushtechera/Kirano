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
    expiry_date: int
    stock_added_at: date

    model_config = ConfigDict(from_attributes=True)


    