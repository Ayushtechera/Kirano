from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from datetime import datetime


class SaleItemCreate(BaseModel):
    barcode : str
    quantity : int  = Field(gt=0)



class SaleCreate(BaseModel):
    items: list[SaleItemCreate] = Field(min_length=1)


class saleItemResponse(BaseModel):
    id: int
    product_id : int
    quantity : int
    unit_price : Decimal
    subtotal : Decimal

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    id: int
    bill_number : str
    total_amount : Decimal
    created_at : datetime
    items: list[saleItemResponse]

class SalePreviewItemResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class SalePreviewResponse(BaseModel):
    sale_items: list[SalePreviewItemResponse]
    total_amount: Decimal


class SaleCheckoutCreate(SaleCreate):
    payment_reference : str