from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from sqlalchemy import func, case



from app.api.categories import get_db
from app.models import Product, InventoryBatch
from app.schemas.inventory import StockInCreate, StockInResponse, InventorySummaryResponse

router = APIRouter(prefix="/inventory", tags=["Inventory"])


# Status priority:
# 1. quantity == 0 → DEPLETED
# 2. expiry_date < date.today() → EXPIRED
# 3. Otherwise → ACTIVE


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

# Status priority:
# 1. quantity == 0 → DEPLETED
# 2. expiry_date < date.today() → EXPIRED
# 3. Otherwise → ACTIVE

@router.get("/product/{product_id}/active", response_model=list[StockInResponse])
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
        InventoryBatch.product_id == product_id,
        InventoryBatch.quantity > 0,
        InventoryBatch.expiry_date >= date.today()
    ).order_by(InventoryBatch.expiry_date.asc()).all()
    return batches

@router.get("/product/{product_id}/history", response_model=list[StockInResponse])
def get_product_batch_history(product_id:int, db: Session = Depends(get_db)):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    batches  = db.query(InventoryBatch).filter(
        InventoryBatch.product_id == product_id
    ).order_by(
        InventoryBatch.expiry_date.asc()
    ).all()

    return batches

@router.get("/summary", response_model=list[InventorySummaryResponse])
def get_inventory_summary(db: Session = Depends(get_db)):

    today = date.today()

    summary = db.query(
        Product.id.label("product_id"),
        Product.name.label("product_name"),

        func.coalesce( # coalesce : It will return 0 if stock is missing.
            func.sum(
                case(  #Case means : we are calculating only valid, non-zero batches which are active
                    ( 
                        (InventoryBatch.quantity > 0) &
                        (InventoryBatch.expiry_date >= today),
                        InventoryBatch.quantity
                    ),
                    else_=0
                )
            ),0
        ).label("total_active_quantity"),

        func.count(InventoryBatch.id).label("total_batches"),#It will count inventory batches of particular products including depleted and expired
        
        func.count(
            case(
                (
                    (InventoryBatch.quantity > 0) & 
                    (InventoryBatch.expiry_date >= today),
                    InventoryBatch.id
                ),
                else_=None
            )
        ).label("total_active_batches"),

        func.coalesce( 
            func.sum(InventoryBatch.quantity),0
        ).label("total_quantity_including_expired")
    
    ).outerjoin( # Outerjoin : It will also consider those products  which don't have batches.
        InventoryBatch,
        Product.id == InventoryBatch.product_id
    ).group_by(
        Product.id,
        Product.name
    ).all()

    return summary 