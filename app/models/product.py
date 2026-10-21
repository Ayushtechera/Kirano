from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from app.db.database import Base
from sqlalchemy.orm import relationship

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    barcode = Column(String(50), unique=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"),nullable=False)
    weight = Column(String(50))
    selling_price = Column(Numeric(10,2), nullable=False)
    cost_price = Column(Numeric(10,2), nullable=False) 
    inventory_batches = relationship("InventoryBatch", back_populates="product")