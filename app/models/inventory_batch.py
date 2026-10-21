from sqlalchemy import Integer, Column, String, Date, DateTime, ForeignKey
from app.db.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship



class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"),nullable=False)
    quantity = Column(Integer, nullable=False)
    expiry_date = Column(Date, nullable=False)
    stock_added_at = Column(DateTime(timezone=True), server_default=func.now())
    product = relationship("Product", back_populates="inventory_batches")