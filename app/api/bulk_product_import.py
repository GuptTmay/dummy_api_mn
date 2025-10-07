from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import time
import pandas as pd
from io import StringIO, BytesIO
from app.db import engine
from openpyxl import load_workbook
import csv
import tempfile

router = APIRouter()



@router.post("/bulk-product-import/v5", summary="Bulk upload products from CSV or Excel")
async def bulk_product_import(file: UploadFile = File(...)):
    start = time.perf_counter()

    if file.filename.endswith((".xls", ".xlsx")):
        # does not work here
        df = pd.read_excel(file.file)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        df.to_csv(tmp.name, index=False)
        csv_file = open(tmp.name, "r")

    elif file.filename.endswith((".csv", ".CSV")):
        csv_file = file.file
    else:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file can be of .csv or .xlsx type only!!",
        )

    process_end = time.perf_counter()
    
    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            # cur.execute("SET work_mem = '256MB';")

            cur.copy_expert(
                """
                COPY product(product_id, name, people, category, price, stock_quantity,
                             manufacturer, description)
                FROM STDIN WITH CSV HEADER
                """,
                csv_file,
            )
            imported_count = cur.rowcount
        conn.commit()
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": f"Insert failed: {e}"}
    finally:
        conn.close()

    end = time.perf_counter()
    return {
        "status": "success",
        "imported_count": imported_count,
        "timeTaken_ms": round((end - start) * 1000, 2),
        "Data Processing TimeTaken_ms": round((process_end - start) * 1000, 2),
    }