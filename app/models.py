from sqlmodel import SQLModel, Field
import uuid


class Product(SQLModel, table=True):
    product_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, index=True, primary_key=True
    )
    name: str = Field(index=False, nullable=False)
    people: str = Field(index=True)
    category: str = Field(index=False, nullable=False)
    price: float = Field(gt=0, nullable=False)
    stock_quantity: int = Field(ge=0, default=0)
    manufacturer: str
    description: str

