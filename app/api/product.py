
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func

from app.db.database import get_db
from app.core.dependencies import get_current_vendor
from app.models import Product, Category, InventoryBatch, SaleItem
from app.models.vendor import Vendor
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductDetailResponse, 
    ProductUpdate
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/", response_model=ProductResponse, status_code=201)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    existing = db.query(Product).filter(
        Product.store_id == vendor.store_id,
        Product.barcode == data.barcode.strip()
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Barcode already exists")

    existing_product = db.query(Product).filter(
        Product.store_id == vendor.store_id,
        Product.name.ilike(data.name.strip()),
        Product.weight == data.weight,
        Product.category_id == data.category_id
    ).first()

    if existing_product:
        raise HTTPException(
            status_code=409,
            detail="Similar product already exists. Use the existing product."
        )

    category = db.query(Category).filter(
        Category.id == data.category_id,
        Category.store_id == vendor.store_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        name=data.name.strip(),
        barcode=data.barcode.strip(),
        category_id=data.category_id,
        store_id=vendor.store_id,
        weight=data.weight,
        selling_price=data.selling_price,
        cost_price=data.cost_price,
        reorder_level=data.reorder_level
    )

    db.add(product)

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Product conflicts with existing data"
        )

    return product


@router.get("/barcode/{barcode}", response_model=ProductResponse)
def get_product_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.barcode == barcode.strip(),
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/search", response_model=list[ProductResponse])
def search_products(
    name: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    return db.query(Product).filter(
        Product.name.ilike(f"%{name.strip()}%"),
        Product.store_id == vendor.store_id
    ).all()


@router.get("/", response_model=list[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    return db.query(Product).filter(
        Product.store_id == vendor.store_id
    ).all()


@router.get("/{product_id}/details", response_model=ProductDetailResponse)
def get_product_details(
    product_id: int,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/by-name/{name}", response_model=ProductDetailResponse)
def get_product_by_name(
    name: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.name.ilike(name.strip()),
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/barcode/{barcode}/details", response_model=ProductDetailResponse)
def get_product_by_barcode_details(
    barcode: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.barcode == barcode.strip(),
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/{product_id}/stock")
def get_product_stock(
    product_id: int,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    total_stock = db.query(
        func.coalesce(func.sum(InventoryBatch.quantity), 0)
    ).filter(
        InventoryBatch.product_id == product_id
    ).scalar()

    return {
        "product_id": product_id,
        "product_name": product.name,
        "total_stock": total_stock
    }


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.category_id is not None:
        category = db.query(Category).filter(
            Category.id == data.category_id,
            Category.store_id == vendor.store_id
        ).first()

        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    if data.barcode is not None:
        existing = db.query(Product).filter(
            Product.store_id == vendor.store_id,
            Product.barcode == data.barcode.strip(),
            Product.id != product_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Barcode already exists"
            )
    data.barcode = data.barcode.strip()
    
    update = data.model_dump(exclude_unset=True)

    for field, value in update.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update product")

    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == vendor.store_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    sale_items = db.query(SaleItem).filter(
        SaleItem.product_id == product.id
    ).first()

    if sale_items:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the product. It has associated sales records."
        )

    db.delete(product)
    db.commit()
