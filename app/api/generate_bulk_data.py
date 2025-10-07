import random
import uuid
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from typing import Literal
from faker import Faker
from io import BytesIO, StringIO
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()
fake = Faker()


@router.get(
    "/generate-dummy-product-dataset",
    summary="Generate and download a dummy product dataset",
    response_description="A file download (CSV or Excel) containing the product data.",
)
async def generate_dataset(
    rows: int = 100,
    format: Literal["csv", "excel"] = "csv",
):
    if rows <= 0 or rows > 10000000:
        raise HTTPException(
            status_code=400,
            detail="The 'rows' parameter must be a positive integer, max 10000000.",
        )

    df = generate_product_data(rows)
    filename = f"dummy_products_{rows}"

    if format == "csv":
        # Use StringIO to hold CSV content in memory
        stream = StringIO()
        df.to_csv(stream, index=False, encoding="utf-8")

        # Prepare the response
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}.csv",
                "Content-Type": "text/csv; charset=utf-8",
            },
        )
        return response

    elif format == "excel":
        stream = BytesIO()
        df.to_excel(stream, index=False, sheet_name="Products", engine="openpyxl")
        stream.seek(0)  # Reset stream position

        # Prepare the response
        response = Response(
            content=stream.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}.xlsx",
            },
        )
        return response

    else:
        # Should not be reached due to Literal type hint, but good practice
        raise HTTPException(
            status_code=400,
            detail="Invalid format specified. Must be 'csv' or 'excel'.",
        )


def generate_product_data(num_rows: int) -> pd.DataFrame:
    """Generates a Pandas DataFrame with dummy fashion/clothing product data."""
    data = []

    categories = ["Shirt", "Jeans", "Footwear"]
    people = ["Men", "Women", "Boy", "Girl"]
    colours = ["Pink", "Blue", "Red", "Green"]
    company = ["Nike", "Adidas", "Puma", "Reebok"]

    for i in range(1, num_rows + 1):
        cur_category = random.choice(categories)
        product_name = random.choice(colours) + " " + cur_category

        row = {
            "product_id": uuid.uuid4(),
            "name": product_name,
            "people": random.choice(people),
            "category": cur_category,
            "price": round(random.uniform(10.99, 499.99), 2),
            "stock_quantity": random.randint(0, 500),
            "manufacturer": random.choice(company),
            "description": fake.sentence(nb_words=3),
        }
        data.append(row)

    return pd.DataFrame(data)



