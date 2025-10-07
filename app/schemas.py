from pydantic import BaseModel
from typing import List
from app.models import Product 

class PaginatedResponse(BaseModel):
    """Model for the list endpoint response."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    time: float
    data: List[Product]
