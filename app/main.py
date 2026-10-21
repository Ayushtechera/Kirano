from fastapi import FastAPI


from app.api.categories import router as category_router

app = FastAPI(title="Kirano API")
app.include_router(category_router)

@app.get("/")
def home():
    return {"message": "Kirano API is running"}