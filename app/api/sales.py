from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from uuid import uuid4
from datetime import date,datetime,timezone,timedelta,time
from calendar import monthrange
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from zoneinfo import ZoneInfo

from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.product import Product
from app.models.inventory_batch import InventoryBatch
from app.db.database import get_db
from app.core.dependencies import get_current_vendor
from app.models.vendor import Vendor

from app.schemas.sale import(
    SaleCreate,
    SalePreviewResponse,
    SaleResponse,
    SaleCheckoutCreate,
    SalesSummaryResponse
    )

router = APIRouter(
    prefix="/sales",
    tags=["Sales"]
)

IST = ZoneInfo("Asia/Kolkata")

def verify_payment(payment_reference: str):
    # Temporary testing logic
    return payment_reference == "TEST_SUCCESS"

# Date Filters:
# today(time)       -> From today's 00:00 to tomorrow's 00:00.
# last_7_days(timedelta) -> Today and the previous 6 calendar days.
# this_month(monthrange)  -> From the first day of the current month to the first day of the next month.
# custom      -> User-provided start_date and end_date.

def get_date_range(period: str, start_date: date = None, end_date:date = None):
    today = date.today()

    if period == "today":
        start = datetime.combine(today,time.min,tzinfo=IST)
        end = datetime.combine(today + timedelta(days=1),time.min,tzinfo=IST)

    elif period == "last_7_days":
        start = datetime.combine(today - timedelta(days=6),time.min,tzinfo=IST)
        end = datetime.combine(today + timedelta(days=1),time.min,tzinfo=IST)

    elif period == "this_month":
        start = datetime.combine(today.replace(day=1), time.min,tzinfo=IST)

        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        end = datetime.combine(next_month,time.min,tzinfo=IST)

    elif period == "custom":
        if not start_date or not end_date:
            raise HTTPException(
                status_code=400,
                detail="Both start_date and end_date are required"
            )

        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date cannot be after end_date"
            )

        start = datetime.combine(start_date,time.min,tzinfo=IST)
        end   = datetime.combine(end_date + timedelta(days=1),time.min,tzinfo=IST)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid Period"
        )
    return start,end

# ALWAYS:
# Specific routes first, dynamic routes later.

@router.post("/checkout", response_model=SaleResponse)
def create_sale(data: SaleCheckoutCreate, db: Session = Depends(get_db),vendor: Vendor = Depends(get_current_vendor)):
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
        total_amount = total_amount,
        store_id = vendor.store_id
    )
    try: 
        db.add(sale)
        db.flush()
        for barcode,quantity in aggregated_items.items():
            barcode = barcode.strip()
            #1.Fetching product using barcode
            product = db.query(Product).filter(
                Product.barcode == barcode,
                Product.store_id == vendor.store_id
            ).first()
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with barcode {barcode} not found"
                )
            #2.Fetching inventory batches using FEFO(First Expiry First Out)
            batches = db.query(InventoryBatch).filter(
                InventoryBatch.product_id == product.id,
                InventoryBatch.expiry_date >= date.today(),
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
            total_cost = Decimal("0.00")
            # 5. Deduct inventory using FEFO 
            remaining_quantity = quantity
            for batch in batches:
                if remaining_quantity == 0:
                    break
                deducted_quantity = min(
                    batch.quantity,
                    remaining_quantity
                )
                batch_cost = (
                    batch.unit_cost
                    if batch.unit_cost is not None
                    else product.cost_price
                )

                total_cost += batch_cost * deducted_quantity
                batch.quantity -= deducted_quantity
                remaining_quantity -= deducted_quantity
                if batch.quantity == 0 and batch.depleted_at is None:
                    batch.depleted_at = datetime.now(timezone.utc)
            #6. Create sale item
            sale_item = SaleItem(
                product_id = product.id,
                quantity = quantity,
                unit_price = unit_price,
                subtotal = subtotal,
                unit_cost= total_cost / quantity
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

    except SQLAlchemyError as e:
        db.rollback()
        print("DATABASE ERROR:", repr(e))
        raise HTTPException(
            status_code=500,
            detail = "Billing failed due to a database error"
        )

@router.post("/preview", response_model=SalePreviewResponse)
def preview_sale(data: SaleCreate,db: Session = Depends(get_db),vendor: Vendor = Depends(get_current_vendor)):

    sale_items=[]
    total_amount = Decimal("0.00")
     
    for item in data.items:
        product = db.query(Product).filter(
            Product.barcode == item.barcode,
            Product.store_id == vendor.store_id
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

@router.get("/",response_model=list[SaleResponse])
def get_sale(db: Session = Depends(get_db),vendor: Vendor = Depends(get_current_vendor)):

    sales = db.query(Sale).filter(
        Sale.store_id == vendor.store_id
    ).order_by(
        Sale.created_at.desc()
    ).all()

    return sales

@router.get("/summary", response_model=SalesSummaryResponse)
def get_sales_summary(
    period: str = "today",
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    start, end = get_date_range(period, start_date, end_date)

    # Calculate total revenue and total orders
    sales_result = db.query(
        func.coalesce(func.sum(Sale.total_amount),0).label("total_revenue"),
        func.count(Sale.id).label("total_orders")
    ).filter(
        Sale.created_at >= start,
        Sale.created_at < end,
        Sale.store_id == vendor.store_id
    ).first()

    # Calculate total cost of goods sold
    cogs_result = db.query(
        func.coalesce(
            func.sum(SaleItem.unit_cost * SaleItem.quantity),0
        ).label("total_cogs")
    ).join(
        Sale,SaleItem.sale_id == Sale.id
    ).filter(
        Sale.created_at >= start,
        Sale.created_at < end,
        Sale.store_id == vendor.store_id
    ).first()


    total_revenue = Decimal(str(sales_result.total_revenue))
    total_orders = sales_result.total_orders
    total_cogs = Decimal(str(cogs_result.total_cogs))

    gross_profit = total_revenue - total_cogs

    profit_margin = (
        (gross_profit / total_revenue) * 100
        if total_revenue > 0
        else Decimal("0.00")
    )
    return {
        "start_date": start,
        "end_date": end,
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "total_cogs": total_cogs,
        "gross_profit": gross_profit,
        "profit_margin": profit_margin
    }

@router.get("/{bill_number}", response_model=SaleResponse)
def get_sale(
    bill_number: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    sale = db.query(Sale).filter(
        Sale.bill_number == bill_number,
        Sale.store_id == vendor.store_id
    ).first()

    if not sale:
        raise HTTPException(
            status_code=404,
            detail=f"Sale with BILL-ID: {bill_number} not found"
        )

    return sale