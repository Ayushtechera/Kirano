from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date


from app.api.categories import get_db
from app.models import Product, InventoryBatch
from app.schemas.inventory import StockInCreate, StockInResponse

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/stock-in", response_model=StockInResponse, status_code=201)
def stock_in(data: StockInCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == data.product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.expiry_date <= date.today():
        raise HTTPException(
                status_code=400,
                detail="Expiry date must be in the future"
            )

    batch = InventoryBatch(
        product_id=data.product_id,
        quantity=data.quantity,
        expiry_date=data.expiry_date
    )

    db.add(batch)
    try:
        db.commit()
        db.refresh(batch)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add stock")
    
    return batch


@router.get("/product/{product_id}")
def get_product_batches(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id 
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    batches = db.query(InventoryBatch).filter(
        InventoryBatch.product_id == product_id
    ).order_by(InventoryBatch.expiry_date.asc()).all()

    return batches