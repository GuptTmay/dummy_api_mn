from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import generate_bulk_data, bulk_product_import, get_product_list
from app.db import engine
from app.models import Product
from sqlmodel import SQLModel




@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application has started")
    SQLModel.metadata.create_all(engine)
    yield
    print("Application is shutting down")


# Loading Models 
Product

# Init 
app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"message": "Hello FastAPI"}

app.include_router(generate_bulk_data.router)
app.include_router(bulk_product_import.router)
app.include_router(get_product_list.router)