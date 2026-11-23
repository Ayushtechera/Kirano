import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.config import settings
from app.core.security import oauth2_scheme
from app.models.vendor import Vendor

def get_current_vendor(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        vendor_id = int(payload.get("sub"))

    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_exception

    vendor = db.query(Vendor).filter(
        Vendor.id == vendor_id,
        Vendor.is_active == True
    ).first()

    if vendor is None:
        raise credentials_exception

    return vendor