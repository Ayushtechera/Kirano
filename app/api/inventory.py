from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, timedelta, datetime, timezone
from sqlalchemy import func, case

from app.api.categories import get_db
from app.models import Product, InventoryBatch
from app.schemas.inventory import (
    StockInCreate,
    StockInResponse,
    InventorySummaryResponse,
    InventoryValuationResponse,
    NearExpiryResponse,
    StockAdjustmentCreate
    )

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
        expiry_date=data.expiry_date,
        unit_cost=data.unit_cost
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

@router.get("/valuation", response_model=InventoryValuationResponse)
def get_inventory_valuation(db: Session = Depends(get_db)):
    today = date.today()

    active_stock_value = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        (InventoryBatch.quantity > 0) &
                        (InventoryBatch.expiry_date >= today) & 
                        (InventoryBatch.unit_cost.isnot(None)),
                        InventoryBatch.quantity * InventoryBatch.unit_cost
                    ),
                    else_=0
                )
            ),0       
        )
    ).scalar()

    expired_stock_loss = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        (InventoryBatch.quantity > 0) &
                        (InventoryBatch.expiry_date < today)&
                        (InventoryBatch.unit_cost.isnot(None)),
                        InventoryBatch.quantity * InventoryBatch.unit_cost
                    ),
                    else_=0
                )
            ),0
        )
    ).scalar()

    active_unknown_cost_quantity = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        (InventoryBatch.quantity > 0 ) &
                        (InventoryBatch.expiry_date >= today) &
                        (InventoryBatch.unit_cost.is_(None)),
                        InventoryBatch.quantity
                    ),
                    else_=0
                )
            ),0
        )
    ).scalar()

    expired_unknown_cost_quantity = db.query(
        func.coalesce(
            func.sum(
                case(
                    (
                        (InventoryBatch.quantity > 0) &
                        (InventoryBatch.expiry_date < today) &
                        (InventoryBatch.unit_cost.is_(None)),
                        InventoryBatch.quantity
                    ),
                    else_=0
                )
            )
        ),0
    ).scalar()

    return {
        "active_stock_value": active_stock_value,
        "expired_stock_loss": expired_stock_loss,
        "active_unknown_cost_quantity": active_unknown_cost_quantity,
        "expired_unknown_cost_quantity": expired_unknown_cost_quantity
    }

@router.get("/near-expiry", response_model=list[NearExpiryResponse])
def get_near_expiry_stock(db: Session = Depends(get_db)):
    today = date.today()
    expiry_limit = today + timedelta(days=30)

    near_expiry_batches = db.query(
        InventoryBatch,
        Product.name.label("product_name")
    ).join(
        Product,
        InventoryBatch.product_id == Product.id
    ).filter(
        InventoryBatch.quantity > 0,
        InventoryBatch.expiry_date >= today,
        InventoryBatch.expiry_date <= expiry_limit
    ).order_by(
        InventoryBatch.expiry_date.asc()
    ).all()

    return [
        {
            "product_id": batch.product_id,
            "product_name": product_name,
            "batch_id": batch.id,
            "quantity": batch.quantity,
            "expiry_date": batch.expiry_date,
            "days_until_expiry": (batch.expiry_date - today).days
        }
        for batch, product_name in near_expiry_batches
    ] 

@router.post("/stock-out")
def stock_out(barcode: str, db: Session = Depends(get_db)):

    product = db.query(Product).filter(
        Product.barcode == barcode
    ).first()

    if not product:
        raise HTTPException(404, "Product not found")

    batch = db.query(InventoryBatch).filter(
        InventoryBatch.product_id == product.id,
        InventoryBatch.quantity > 0,
        InventoryBatch.expiry_date >= date.today()
    ).order_by(
        InventoryBatch.expiry_date.asc(),
        InventoryBatch.stock_added_at.asc()
    ).first()

    if not batch:
        raise HTTPException(400, "No active stock available")

    batch.quantity -= 1

    if batch.quantity == 0:
        batch.depleted_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Stock update failed")
    
    remaining_stock = db.query(
        func.coalesce(func.sum(InventoryBatch.quantity), 0)
    ).filter(
        InventoryBatch.product_id == product.id,
        InventoryBatch.quantity > 0,
        InventoryBatch.expiry_date >= date.today()
    ).scalar()

    return {
        "product_id": product.id,
        "product_name": product.name,
        "barcode": product.barcode,
        "quantity_deducted": 1,
        "remaining_stock": remaining_stock,
        "message": "Stock deducted successfully"
    }


@router.get("/low-stock")
def get_low_stock_products(db: Session = Depends(get_db)):
    today = date.today()

    stock = db.query(
        Product.id.label("product_id"),
        Product.name.label("product_name"),
        Product.reorder_level,
        func.coalesce(func.sum(InventoryBatch.quantity), 0).label("current_stock")
    ).outerjoin(
        InventoryBatch,
        (InventoryBatch.product_id == Product.id) &
        (InventoryBatch.quantity > 0) &
        (InventoryBatch.expiry_date >= today)
    ).group_by(
        Product.id,
        Product.name,
        Product.reorder_level
    ).having(
        func.coalesce(func.sum(InventoryBatch.quantity), 0)
        <= Product.reorder_level
    ).all()

    return [
        {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "reorder_level": row.reorder_level,
            "current_stock": row.current_stock,
            "stock_status": (
                "OUT_OF_STOCK" if row.current_stock == 0
                else "LOW_STOCK"
            )
        }
        for row in stock
    ]


@router.post("/adjust-stock")
def adjust_stock(data: StockAdjustmentCreate, db: Session = Depends(get_db)):

    if data.quantity == 0:
        raise HTTPException(400, "Adjustment quantity cannot be zero")

    product = db.query(Product).filter(
        Product.id == data.product_id
    ).first()

    if not product:
        raise HTTPException(404, "Product not found")

    remaining = abs(data.quantity)

    if data.quantity < 0:
        batches = db.query(InventoryBatch).filter(
            InventoryBatch.product_id == product.id,
            InventoryBatch.quantity > 0,
            InventoryBatch.expiry_date >= date.today()
        ).order_by(
            InventoryBatch.expiry_date.asc(),
            InventoryBatch.stock_added_at.asc()
        ).all()

        available = sum(batch.quantity for batch in batches)

        if available < remaining:
            raise HTTPException(400, "Insufficient active stock")

        for batch in batches:
            deducted = min(batch.quantity, remaining)
            batch.quantity -= deducted
            remaining -= deducted

            if batch.quantity == 0:
                batch.depleted_at = datetime.now(timezone.utc)

            if remaining == 0:
                break

    else:
        raise HTTPException(
            400,
            "For additional stock, use the stock-in endpoint"
        )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(500, "Stock adjustment failed")

    return {
        "product_id": product.id,
        "product_name": product.name,
        "adjusted_quantity": data.quantity,
        "reason": data.reason,
        "message": "Stock adjusted successfully"
    }