
from sqlalchemy import Column, Integer, String, Numeric, DateTime, func,ForeignKey,UniqueConstraint
from sqlalchemy.orm import relationship


from app.db.database import Base

class Sale(Base):
    __tablename__= "sales"

    __table_args__ = (
        UniqueConstraint("store_id", "bill_number", name="uq_sale_store_bill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String(50), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)


    items = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan"
    )