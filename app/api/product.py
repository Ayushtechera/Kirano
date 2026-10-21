from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.categories import get_db
from app.models import Product, Category
from app.schemas.product import ProductCreate,ProductResponse,ProductDetailResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/",response_model=ProductResponse,status_code=201)
def create_product(data: ProductCreate,db: Session = Depends(get_db)):
    existing = db.query(Product).filter(
        Product.barcode == data.barcode.strip()
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="Barcode already exists")

    category = db.query(Category).filter(
        Category.id == data.category_id
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        name=data.name.strip(),
        barcode=data.barcode.strip(),
        category_id=data.category_id,
        weight=data.weight,
        selling_price=data.selling_price,
        cost_price=data.cost_price
    )

    db.add(product)
    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product conflicts with existing data")

    return product



@router.get("/barcode/{barcode}", response_model=ProductResponse)
def get_product_by_barcode(barcode:str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.barcode == barcode.strip()
    ).first()


    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/search", response_model=list[ProductResponse])
def search_products(
    name:str,
    db: Session = Depends(get_db)
):
    return db.query(Product).filter(
        Product.name.ilike(f"%{name.strip()}%")
    ).all()


@router.get("/", response_model=list[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.get("/{product_id}/details", response_model=ProductDetailResponse)
def get_product_details(
    product_id: int,
    db: Session = Depends(get_db)
):

    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.get("/by-name/{name}", response_model=ProductDetailResponse)
def get_product_by_name(name: str, db: Session = Depends(get_db)):

    product = db.query(Product).filter(
        Product.name.ilike(name.strip())
    ).first()

    if not product:
        raise HTTPException(status_code=404 , detail="Product not found")

    return product


@router.get("/barcode/{barcode}/details", response_model=ProductDetailResponse)
def get_product_by_barcode_details(
    barcode: str,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.barcode == barcode.strip()
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product

