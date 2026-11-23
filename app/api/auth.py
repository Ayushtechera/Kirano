
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.database import get_db
from app.models.store import Store
from app.models.vendor import Vendor
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.core.dependencies import get_current_vendor

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    existing_vendor = db.query(Vendor).filter(
        Vendor.email == data.email
    ).first()

    if existing_vendor:
        raise HTTPException(status_code=409, detail="Email already registered")

    store = Store(name=data.store_name.strip())

    try:
        db.add(store)
        db.flush()

        vendor = Vendor(
            email=data.email,
            hashed_password=hash_password(data.password),
            store_id=store.id
        )

        db.add(vendor)
        db.commit()
        db.refresh(vendor)

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    return {
        "access_token": create_access_token(vendor.id),
        "token_type": "bearer"
    }


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):

    vendor = db.query(Vendor).filter(
        Vendor.email == data.email
    ).first()

    if not vendor or not verify_password(
        data.password, vendor.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not vendor.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    return {
        "access_token": create_access_token(vendor.id),
        "token_type": "bearer"
    }

@router.get("/me")
def get_me(vendor: Vendor = Depends(get_current_vendor)):
    return {
        "vendor_id": vendor.id,
        "email": vendor.email,
        "store_id": vendor.store_id,
        "store_name": vendor.store.name
    }