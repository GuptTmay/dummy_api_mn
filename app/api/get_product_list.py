
from fastapi import APIRouter, Depends, HTTPException, Query
import time
from app.schemas import PaginatedResponse 
from app.db import get_session
from typing import Optional
from sqlmodel import Session, select
from app.models import Product
from meilisearch.errors import MeilisearchApiError
from app.meili import client 
from app.typesense import client as tsClient



router = APIRouter()
# tsClient = typesense.Client({
#   'nodes': [{ 'host': 'localhost', 'port': '8108', 'protocol': 'http' }],
#   'api_key': 'sampleTypesenseKey'
# })



@router.post("/get-product-list/meilisearch", 
    response_model=PaginatedResponse,
    summary="Get a paginated, searchable, and filterable list of products"
)
async def get_product_list(
    # Pagination Parameters
    page: int = Query(1, ge=1, description="Page number to retrieve."),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page."),
    
    # Search and Filtration Parameters
    search: Optional[str] = Query(None, description="Search term for product name or manufacturer."),
    people: Optional[str] = Query(None, description="Filter by product user (case-insensitive)."),
    category: Optional[str] = Query(None, description="Filter by categories."),
    min_price: Optional[float] = Query(None, ge=0, description="Filter products with price greater than or equal to this value."),
    session: Session = Depends(get_session) 
):
    start = time.perf_counter()
    
    # Validate that both people and category are provided
    if not people or not category:
        raise HTTPException(
            status_code=400,
            detail="Both 'people' and 'category' parameters are required."
        )
    
    # Create index name from people and category
    index_name = f"{people.lower()}-{category.lower()}".replace(" ", "-")

    try:
        # Try to get existing index
        index = client.get_index(index_name)
        print(f"✅ Index '{index_name}' already exists")
        
    except MeilisearchApiError as e:
        print(f"❌ Index '{index_name}' does not exist. Creating...")
        
        query = select(Product).where(
            (Product.people.ilike(f"{people}%")),
            (Product.category.ilike(f"%{category}%")),
        )
        
        results = session.exec(query).all()

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No products found for people='{people}' and category='{category}'."
            )
        
        # Convert SQLModel objects to dictionaries and handle UUID serialization
        documents = []
        for product in results:
            product_dict = product.model_dump()
            # Convert UUID to string for JSON serialization
            if 'product_id' in product_dict and product_dict['product_id'] is not None:
                product_dict['product_id'] = str(product_dict['product_id'])
            documents.append(product_dict)
        
        # Create index with primary key - use attribute access, not dictionary
        create_task = client.create_index(index_name, {'primaryKey': 'product_id'})
        client.wait_for_task(create_task.task_uid)  # Use .task_uid not ['taskUid']
        print(f"✅ Index '{index_name}' created")
        
        index = client.get_index(index_name)
        
        filterable_task = index.update_filterable_attributes(['price'])
        searchable_task = index.update_searchable_attributes(['name', 'manufacturer', 'description'])

        client.wait_for_task(filterable_task.task_uid)  # Use .task_uid
        client.wait_for_task(searchable_task.task_uid)  # Use .task_uid
        print(f"✅ Settings configured for index '{index_name}'")
        
        # Add documents and wait for indexing to complete
        add_docs_task = index.add_documents(documents)
        client.wait_for_task(add_docs_task.task_uid)  # Use .task_uid
        
        print(f"✅ {len(documents)} documents added to index '{index_name}'")
    
    # Build filter string (only for min_price)
    filter_str = None
    if min_price is not None:
        filter_str = f"price >= {min_price}"
    
    # Perform search
    search_params = {
        "limit": page_size,
        "offset": (page - 1) * page_size
    }
    
    # if filter_str:
    search_params["filter"] = filter_str
    
    result = index.search(search or "", search_params)
    
    # Extract results
    paginated_products = result.get("hits", [])
    total_items = result.get("estimatedTotalHits", 0)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    
    # Check if requested page exists
    if page > total_pages and total_items > 0:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page} does not exist. Last page is {total_pages}.",
        )

    end = time.perf_counter()
    
    # Return paginated response
    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        time=round((end - start) * 1000, 2),
        data=paginated_products,
    )




@router.post("/get-product-list/meilisearch/v2", 
    response_model=PaginatedResponse,
    summary="Get a paginated, searchable, and filterable list of products"
)
async def get_product_list_v2(
    # Pagination Parameters
    page: int = Query(1, ge=1, description="Page number to retrieve."),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page."),
    
    # Search and Filtration Parameters
    search: Optional[str] = Query(None, description="Search term for product name or manufacturer."),
    people: Optional[str] = Query(None, description="Filter by product user (case-insensitive)."),
    category: Optional[str] = Query(None, description="Filter by categories."),
    min_price: Optional[float] = Query(None, ge=0, description="Filter products with price greater than or equal to this value."),
    session: Session = Depends(get_session) 
):
    start = time.perf_counter()
    
    # Validate that both people and category are provided
    if not category:
        raise HTTPException(
            status_code=400,
            detail="'category' parameters is required."
        )
    
    try:
        # Try to get existing index
        index = client.get_index(category.lower())
        print(f"✅ Index '{category.lower()}' already exists")
        
    except MeilisearchApiError as e:
        print(f"❌ Index '{category.lower()}' does not exist. Creating...")
        
        query = select(Product).where(
            (Product.category.ilike(f"%{category}%")),
        )
        
        results = session.exec(query).all()

        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No products found for category='{category}'."
            )
        
        documents = []
        for product in results:
            product_dict = product.model_dump()
            # Convert UUID to string for JSON serialization
            if 'product_id' in product_dict and product_dict['product_id'] is not None:
                product_dict['product_id'] = str(product_dict['product_id'])
            documents.append(product_dict)
        
        create_task = client.create_index(category.lower(), {'primaryKey': 'product_id'})
        client.wait_for_task(create_task.task_uid) 
        print(f"✅ Index '{category.lower()}' created")
        
        index = client.get_index(category.lower())
        filterable_task = index.update_filterable_attributes(['price', 'people']) 
        searchable_task = index.update_searchable_attributes(['name', 'manufacturer', 'description'])

        client.wait_for_task(filterable_task.task_uid)  
        client.wait_for_task(searchable_task.task_uid)  
        print(f"✅ Settings configured for index '{category.lower()}'")
        
        # Add documents and wait for indexing to complete
        add_docs_task = index.add_documents(documents)
        client.wait_for_task(add_docs_task.task_uid,  timeout_in_ms=25000) 
        
        print(f"✅ {len(documents)} documents added to index '{category.lower()}'")
    
    # Build filter string (only for min_price)
    filter_by = []
    if min_price is not None:
        filter_by.append(f"price >= {min_price}")
    if people is not None:
        filter_by.append(f'people = "{people}"')

    filter_by = " AND ".join(filter_by) if filter_by else ""
        # Perform search
    search_params = {
        "limit": page_size,
        "offset": (page - 1) * page_size
    }
    
    # if filter_str:
    search_params["filter"] = filter_by 
    
    result = index.search(search or "", search_params)
    
    # Extract results
    paginated_products = result.get("hits", [])
    total_items = result.get("estimatedTotalHits", 0)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
    
    # Check if requested page exists
    if page > total_pages and total_items > 0:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page} does not exist. Last page is {total_pages}.",
        )

    end = time.perf_counter()
    
    # Return paginated response
    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        time=round((end - start) * 1000, 2),
        data=paginated_products,
    )





@router.post("/get-product-list/typesense",
    response_model=PaginatedResponse,
    summary="Get paginated, searchable, filterable list of products (Typesense)"
)
async def get_product_list_typesense(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    people: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    session: Session = Depends(get_session)
):
    start = time.perf_counter()

    if not people or not category:
        raise HTTPException(status_code=400, detail="Both 'people' and 'category' are required.")

    index_name = f"{people.lower()}-{category.lower()}".replace(" ", "-")

    # Check if collection exists
    try:
        tsClient.collections[index_name].retrieve()
        print(f"✅ Collection '{index_name}' exists")
    except Exception:
        print(f"❌ Collection '{index_name}' not found. Creating...")

        query = select(Product).where(
            (Product.people.ilike(f"{people}%")),
            (Product.category.ilike(f"%{category}%")),
        )
        results = session.exec(query).all()

        if not results:
            raise HTTPException(status_code=404, detail=f"No products found for {people}/{category}")

        documents = []
        for product in results:
            d = product.model_dump()
            d["product_id"] = str(d["product_id"])
            documents.append(d)

        schema = {
            "name": index_name,
            "fields": [
                {"name": "product_id", "type": "string"},
                {"name": "name", "type": "string"},
                {"name": "people", "type": "string"},
                {"name": "category", "type": "string"},
                {"name": "price", "type": "float"},
                {"name": "stock_quantity", "type": "int32"},
                {"name": "manufacturer", "type": "string"},
                {"name": "description", "type": "string"},
            ],
            "default_sorting_field": "price"
        }

        tsClient.collections.create(schema)
        tsClient.collections[index_name].documents.import_(documents, {'action': 'create'})
        print(f"✅ {len(documents)} documents indexed in '{index_name}'")

    # Build filter
    filter_by = f"price:>={min_price}" if min_price is not None else ""

    search_params = {
        "q": search or "*",
        "query_by": "name,manufacturer,description",
        "filter_by": filter_by,
        "per_page": page_size,
        "page": page
    }

    result = tsClient.collections[index_name].documents.search(search_params)
    hits = result.get("hits", [])
    total_items = result.get("found", 0)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1

    if page > total_pages and total_items > 0:
        raise HTTPException(status_code=404, detail=f"Page {page} does not exist (max {total_pages}).")

    end = time.perf_counter()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        time=round((end - start) * 1000, 2),
        data=[h["document"] for h in hits],
    )



@router.post("/get-product-list/typesense/v2",
    response_model=PaginatedResponse,
    summary="Get paginated, searchable, filterable list of products (Typesense)"
)
async def get_product_list_typesense_v2(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    people: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    session: Session = Depends(get_session)
):
    start = time.perf_counter()

    if not category:
        raise HTTPException(status_code=400, detail="'category' is required.")


    # Check if collection exists
    try:
        tsClient.collections[category].retrieve()
        print(f"✅ Collection '{category}' exists")
    except Exception:
        print(f"❌ Collection '{category}' not found. Creating...")

        query = select(Product).where(
            (Product.category.ilike(f"%{category}%")),
        )
        results = session.exec(query).all()

        if not results:
            raise HTTPException(status_code=404, detail=f"No products found for {category}")

        documents = []
        for product in results:
            d = product.model_dump()
            d["product_id"] = str(d["product_id"])
            documents.append(d)

        schema = {
            "name": category,
            "fields": [
                {"name": "product_id", "type": "string"},
                {"name": "name", "type": "string"},
                {"name": "people", "type": "string"},
                {"name": "category", "type": "string"},
                {"name": "price", "type": "float"},
                {"name": "stock_quantity", "type": "int32"},
                {"name": "manufacturer", "type": "string"},
                {"name": "description", "type": "string"},
            ],
            "default_sorting_field": "price"
        }

        tsClient.collections.create(schema)
        tsClient.collections[category].documents.import_(documents, {'action': 'create'})
        print(f"✅ {len(documents)} documents indexed in '{category}'")

    filter_by = []

    if min_price is not None:
        filter_by.append(f"price:>={min_price}")
    if people is not None:
        filter_by.append(f'people:={people}')

    filter_by = " && ".join(filter_by) if filter_by else ""


    search_params = {
        "q": search or "*",
        "query_by": "name,manufacturer,description",
        "filter_by": filter_by,
        "per_page": page_size,
        "page": page
    }

    result = tsClient.collections[category].documents.search(search_params)
    hits = result.get("hits", [])
    total_items = result.get("found", 0)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1

    if page > total_pages and total_items > 0:
        raise HTTPException(status_code=404, detail=f"Page {page} does not exist (max {total_pages}).")

    end = time.perf_counter()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        time=round((end - start) * 1000, 2),
        data=[h["document"] for h in hits],
    )

