from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy import func
from app.db.database import SessionLocal
from app.models import Category
from app.schemas.category import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(
        func.lower(Category.name) == data.name.strip().lower()
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Category already exists")

    category = Category(name = data.name)
    db.add(category)
    db.commit()
    db.refresh(category)

    return category


@router.get("/", response_model=list[CategoryResponse])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()


@router.delete("/{category_name}", status_code=204)
def delete_category(
    category_name: str,
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(
        func.lower(Category.name) == category_name.strip().lower()
    ).first()

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found"
        )

    db.delete(category)
    db.commit()
    
