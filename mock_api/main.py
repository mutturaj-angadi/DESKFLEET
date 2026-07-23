"""
mock_api.main
==============
A tiny, deterministic stand-in for a real order/product REST API.

The public FakeStoreAPI is fine for a demo but is rate-limited and
occasionally flaky, which makes agent behaviour hard to test
reproducibly. This mock serves the same *shape* of data from fixed
in-memory fixtures so DeskFleet's Researcher agent always gets
consistent, predictable responses in dev, tests, and CI.

Run standalone with:
    uvicorn mock_api.main:app --port 9000 --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="DeskFleet Mock Order/Product API", version="1.0.0")


class Product(BaseModel):
    product_id: str
    title: str
    category: str
    price: float
    description: str
    in_stock: bool


class Order(BaseModel):
    order_id: str
    customer_email: str
    product_id: str
    status: str
    placed_at: str
    eta: str | None = None
    tracking_number: str | None = None


PRODUCTS: dict[str, Product] = {
    "P-1001": Product(
        product_id="P-1001",
        title="Aurora Wireless Headphones",
        category="electronics",
        price=79.99,
        description="Over-ear wireless headphones with active noise cancellation "
        "and 30-hour battery life.",
        in_stock=True,
    ),
    "P-1002": Product(
        product_id="P-1002",
        title="Trailblazer 30L Backpack",
        category="outdoors",
        price=64.50,
        description="Weatherproof 30-liter hiking backpack with padded straps "
        "and a dedicated laptop sleeve.",
        in_stock=True,
    ),
    "P-1003": Product(
        product_id="P-1003",
        title="Lumen Desk Lamp",
        category="home",
        price=34.00,
        description="Dimmable LED desk lamp with USB-C charging port and "
        "adjustable color temperature.",
        in_stock=False,
    ),
    "P-1004": Product(
        product_id="P-1004",
        title="Cascade Steel Water Bottle",
        category="outdoors",
        price=22.00,
        description="Insulated 750ml steel water bottle, keeps drinks cold for 24 hours.",
        in_stock=True,
    ),
}

ORDERS: dict[str, Order] = {
    "ORD-5001": Order(
        order_id="ORD-5001",
        customer_email="jane.doe@example.com",
        product_id="P-1001",
        status="shipped",
        placed_at="2026-07-01T10:00:00Z",
        eta="2026-07-18",
        tracking_number="TRK-88213",
    ),
    "ORD-5002": Order(
        order_id="ORD-5002",
        customer_email="sam.lee@example.com",
        product_id="P-1003",
        status="delayed",
        placed_at="2026-07-03T14:30:00Z",
        eta="2026-07-25",
        tracking_number="TRK-88214",
    ),
    "ORD-5003": Order(
        order_id="ORD-5003",
        customer_email="alex.kim@example.com",
        product_id="P-1002",
        status="delivered",
        placed_at="2026-06-20T09:15:00Z",
        eta="2026-06-28",
        tracking_number="TRK-88109",
    ),
    "ORD-5004": Order(
        order_id="ORD-5004",
        customer_email="priya.n@example.com",
        product_id="P-1004",
        status="processing",
        placed_at="2026-07-14T08:00:00Z",
        eta="2026-07-20",
        tracking_number=None,
    ),
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    order = ORDERS.get(order_id.upper())
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found")
    return order


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    product = PRODUCTS.get(product_id.upper())
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return product


@app.get("/products", response_model=list[Product])
def search_products(query: str = "") -> list[Product]:
    q = query.lower().strip()
    if not q:
        return list(PRODUCTS.values())
    return [
        p
        for p in PRODUCTS.values()
        if q in p.title.lower() or q in p.description.lower() or q in p.category.lower()
    ]
