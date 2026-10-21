from fastapi import FastAPI


from app.api.categories import router as category_router
from app.api.product import router as product_router
from app.api.inventory import router as inventory_router

app = FastAPI(title="Kirano API")

app.include_router(category_router)
app.include_router(product_router)
app.include_router(inventory_router)

@app.get("/")
def home():
    return {"message": "Kirano API is running"}

