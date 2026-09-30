from typing import Any, Dict, List

from database.database import get_db


class InventoryService:
    def __init__(self) -> None:
        self.db = get_db()

    def list_products(self) -> List[Dict[str, Any]]:
        return list(self.db.products.find({"is_active": True}))

    def add_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        result = self.db.products.insert_one(product)
        product["_id"] = result.inserted_id
        return product

    def get_stock(self, product_id: str) -> int:
        product = self.db.products.find_one({"_id": product_id})
        return product.get("stock", 0) if product else 0
