from sqlalchemy import Column, Integer, String,ForeignKey,UniqueConstraint
from app.db.database import Base


class Category(Base):
    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint("store_id","name",name="uq_category_store_name"),
    )

    id = Column(Integer,primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)