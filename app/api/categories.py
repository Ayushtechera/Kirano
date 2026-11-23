from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.dependencies import get_current_vendor

from app.models import Category, Product
# from app.models.product import Product
from app.db.database import SessionLocal, get_db
from app.models.vendor import Vendor
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), vendor: Vendor = Depends(get_current_vendor)):
    
    name = data.name.strip()

    existing = db.query(Category).filter(
        Category.store_id == vendor.store_id,
        func.lower(Category.name) == data.name.strip().lower()
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Category already exists")

    category = Category(name=name, store_id=vendor.store_id)

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


@router.get("/", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db),vendor: Vendor = Depends(get_current_vendor)):
    return db.query(Category).filter(
        Category.store_id == vendor.store_id
    ).all()



@router.delete("/{category_name}", status_code=204)
def delete_category(
    category_name: str,
    db: Session = Depends(get_db),
    vendor: Vendor = Depends(get_current_vendor)
):
    category = db.query(Category).filter(
        Category.store_id == vendor.store_id,
        func.lower(Category.name) == category_name.strip().lower()
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product = db.query(Product).filter(
        Product.category_id == category.id,
        Product.store_id == vendor.store_id
    ).first()

    if product:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete category. Products are associated with this category."
        )

    db.delete(category)
    db.commit()