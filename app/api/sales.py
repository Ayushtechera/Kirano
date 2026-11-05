from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from uuid import uuid4
from datetime import date
from sqlalchemy.exc import SQLAlchemyError

from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.product import Product
from app.models.inventory_batch import InventoryBatch
from app.db.database import SessionLocal

from app.schemas.sale import(
    SaleCreate,
    SalePreviewResponse,
    SaleResponse,
    SaleCheckoutCreate)

router = APIRouter(
    prefix="/sales",
    tags=["Sales"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_payment(payment_reference: str):
    # Temporary testing logic
    return payment_reference == "TEST_SUCCESS"

  

@router.post("/checkout", response_model=SaleResponse)
def create_sale(data: SaleCheckoutCreate, db: Session = Depends(get_db)):

    if not verify_payment(data.payment_reference):
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed"
        )

    aggregated_items = {}

    for item in data.items:
        if item.barcode in aggregated_items:
            aggregated_items[item.barcode] += item.quantity
        else:
            aggregated_items[item.barcode] = item.quantity

    total_amount = Decimal("0.00")

    sale = Sale(
        bill_number = f"BILL-{uuid4().hex[:10].upper()}",
        total_amount = total_amount
    )

    try: 
        db.add(sale)
        db.flush()

        for barcode,quantity in aggregated_items.items():

            #1.Fetching product using barcode
            product = db.query(Product).filter(
                Product.barcode == barcode
            ).first()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with barcode {barcode} not found"
                )

            #2.Fetching inventory batches using FEFO(First Expiry First Out)
            batches = db.query(InventoryBatch).filter(
                InventoryBatch.product_id == product.id,
                InventoryBatch.expiry_date > date.today(),
                InventoryBatch.quantity > 0
            ).order_by(
                InventoryBatch.expiry_date.asc(),
                InventoryBatch.stock_added_at.asc()
            ).with_for_update().all()

            # This with_for_update() is used to :
            # Locks the selected inventory batch rows to prevent concurrent transactions
            # from modifying the same stock until the current transaction is completed.


            #3. Checking if stock is avaible or not
            available_stock = sum(batch.quantity for batch in batches)

            if available_stock < quantity:
                raise HTTPException(
                    status_code=400,  
                    detail = f"Insufficient stock for {product.name}"
                )

            #4. calculating price
            unit_price = product.selling_price
            subtotal = unit_price * quantity

            # 5. Deduct inventory using FEFO 
            remaining_quantity = quantity

            for batch in batches:

                if remaining_quantity == 0:
                    break

                deducted_quantity = min(
                    batch.quantity,
                    remaining_quantity
                )

                batch.quantity -= deducted_quantity
                remaining_quantity -= deducted_quantity

            #6. Create sale item
            sale_item = SaleItem(
                product_id = product.id,
                quantity = quantity,
                unit_price = unit_price,
                subtotal = subtotal
            )

            sale.items.append(sale_item)

            total_amount += subtotal

        # 7. Update total amount
        sale.total_amount = total_amount

        # 8. Commit transaction
        db.commit()
        db.refresh(sale)

        return sale

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail = "Billing failed due to a database error"
        )



@router.post("/preview", response_model=SalePreviewResponse)
def preview_sale(data: SaleCreate,db: Session = Depends(get_db)):

    sale_items=[]
    total_amount = Decimal("0.00")
     
    for item in data.items:
        product = db.query(Product).filter(
            Product.barcode == item.barcode
        ).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product with barcode {item.barcode} not found"
            )

        unit_price = product.selling_price

        subtotal = unit_price * item.quantity

        total_amount += subtotal

        sale_item = {
            "product_id": product.id,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "subtotal": subtotal
        }

        sale_items.append(sale_item)

    preview_response = {
        "sale_items": sale_items,
        "total_amount": total_amount
    }

    return preview_response



# @router.post("/checkout", response_model=SaleResponse)
# def checkout_sale(data: SaleCheckoutCreate, db: Session = Depends(get_db)):
#     if not verify_payment(data.payment_reference):
#         raise HTTPException(
#             status_code=400,
#             detail="Payment verification failed"
#         )

#     total_amount = Decimal("0.00")

#     sale = Sale(
#         bill_number = f"BILL-{uuid4().hex[:10].upper()}",
#         total_amount = total_amount
#     )

#     db.add(sale)
#     db.flush()

#     for item in data.items:
#         product = db.query(Product).filter(
#             Product.barcode == item.barcode
#         ).first()
#         if not product:
#             raise HTTPException(
#                 status_code=404,
#                 details = f"Product with barcode {item.barcode} not found"
#             )

