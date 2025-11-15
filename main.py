import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product as ProductSchema

app = FastAPI(title="Fragrance Shop API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image: Optional[str] = None


# Utilities

def serialize_doc(doc: dict) -> dict:
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert datetime to isoformat if present
    for k, v in list(d.items()):
        try:
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        except Exception:
            pass
    return d


@app.get("/")
def read_root():
    return {"message": "Fragrance Shop API running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", None) or ("✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set")
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["connection_status"] = "Connected"
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Product endpoints
@app.get("/api/products", response_model=List[dict])
def list_products(limit: int = 24):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    items = get_documents("product", {}, limit)
    if not items:
        # Seed a few minimal products if empty
        seed_items = [
            {
                "title": "Aurora No.1",
                "description": "Iridescent floral-citrus blend with a glassy clean finish.",
                "price": 89.0,
                "category": "fragrance",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1611930022073-b7a4ba5fcccd?q=80&w=1200&auto=format&fit=crop"
            },
            {
                "title": "Serene Veil",
                "description": "Powdery musk wrapped in pear and violet.",
                "price": 72.0,
                "category": "fragrance",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1608571424167-0c2f5b7c1686?q=80&w=1200&auto=format&fit=crop"
            },
            {
                "title": "Prism Eau",
                "description": "Mineral-ozonic notes with a hint of neroli.",
                "price": 96.0,
                "category": "fragrance",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1541643600914-78b084683601?q=80&w=1200&auto=format&fit=crop"
            }
        ]
        for s in seed_items:
            create_document("product", s)
        items = get_documents("product", {}, limit)
    return [serialize_doc(d) for d in items]


@app.post("/api/products", status_code=201)
def create_product(product: ProductCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Validate with Product schema
    _ = ProductSchema(
        title=product.title,
        description=product.description,
        price=product.price,
        category=product.category,
        in_stock=product.in_stock,
    )
    new_id = create_document("product", {**product.model_dump()})
    doc = db["product"].find_one({"_id": ObjectId(new_id)})
    return serialize_doc(doc)


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["product"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
