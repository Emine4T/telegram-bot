from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


PRODUCT_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "smartphone-1",
        "category": "electronics",
        "name": "Smartphone",
        "name_am": "ስማርትፎን",
        "description": "High-quality smartphone with modern features.",
        "description_am": "ጥራት ያለው ዘመናዊ ስማርትፎን።",
        "price": 25000,
        "stock_quantity": 8,
        "sizes": [],
        "colors": ["Black", "White", "Blue"],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=80",
    },
    {
        "id": "headphones-1",
        "category": "electronics",
        "name": "Headphones",
        "name_am": "ሃድፎኖች",
        "description": "Noise-canceling headphones for daily use.",
        "description_am": "ለዕለታዊ አጠቃቀም የሚስማሙ የድምፅ ማጥፊያ ሃድፎኖች።",
        "price": 4500,
        "stock_quantity": 12,
        "sizes": [],
        "colors": ["Black", "Silver"],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80",
    },
    {
        "id": "sneaker-1",
        "category": "shoes",
        "name": "Sneakers",
        "name_am": "ስኒከርስ",
        "description": "Comfortable and stylish everyday sneakers.",
        "description_am": "ምቹ እና በአምልኮ የሚያማሩ የዕለት ተዕለት ጫማዎች።",
        "price": 3000,
        "stock_quantity": 16,
        "sizes": [],
        "colors": ["White", "Black"],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80",
    },
    {
        "id": "boots-1",
        "category": "shoes",
        "name": "Formal Shoes",
        "name_am": "መደበኛ ጫማ",
        "description": "Formal shoes suitable for office use.",
        "description_am": "ለቢሮ እና መደበኛ ክስተቶች ተስማሚ መደበኛ ጫማ።",
        "price": 5200,
        "stock_quantity": 9,
        "sizes": [],
        "colors": ["Black", "Brown"],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=800&q=80",
    },
    {
        "id": "tshirt-1",
        "category": "clothes",
        "name": "T-Shirt",
        "name_am": "ቲ-ሻርት",
        "description": "Soft cotton t-shirt for everyday comfort.",
        "description_am": "ለዕለት ተዕለት እንቆቅልሽ የሚሰጥ ለስላሳ ኮቶን ቲ-ሻርት።",
        "price": 1200,
        "stock_quantity": 20,
        "sizes": [],
        "colors": ["Black", "White", "Gray"],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80",
    },
    {
        "id": "jeans-1",
        "category": "clothes",
        "name": "Jeans",
        "name_am": "ጂንስ",
        "description": "Classic denim jeans for casual and daily wear.",
        "description_am": "የተለመደ የዴንም ጂንስ ለእለት ተዕለት እና ካዝያል ልብስ።",
        "price": 2100,
        "stock_quantity": 15,
        "sizes": [],
        "colors": ["Blue", "Black"],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=800&q=80",
    },
    {
        "id": "vitamin-1",
        "category": "drugstore",
        "name": "Vitamin C",
        "name_am": "ቪታሚን ሲ",
        "description": "Daily vitamin supplement for general wellness.",
        "description_am": "ለአጠቃላይ የጤና እንክብካቤ የዕለት ተዕለት ቪታሚን ተጨማሪ።",
        "price": 850,
        "stock_quantity": 30,
        "sizes": [],
        "colors": [],
        "status": "available",
        "image_url": "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?auto=format&fit=crop&w=800&q=80",
    },
]


class InventoryService:
    @staticmethod
    def _database_dependencies():
        try:
            from ehd_shope.database.database import SessionLocal
            from ehd_shope.database.models import Category, Product
        except ImportError:
            from database.database import SessionLocal
            from database.models import Category, Product
        return SessionLocal, Category, Product

    @staticmethod
    def _product_from_database(product: Any) -> Dict[str, Any]:
        stored_image = product.image_file_id or ""
        image_source_type = "photo"
        if stored_image.startswith("document:"):
            image_source_type = "document"
            stored_image = stored_image.removeprefix("document:")
        return {
            "id": str(product.id),
            "category": product.category.slug,
            "name": product.name,
            "name_am": product.name_am or product.name,
            "description": product.description or "",
            "description_am": product.description_am or "",
            "price": float(product.price),
            "stock_quantity": int(product.stock_quantity or 0),
            "sizes": [],
            "colors": [],
            "status": product.status,
            "is_active": product.status != "hidden",
            "image_file_id": stored_image or None,
            "image_url": stored_image or None,
            "image_source_type": image_source_type if stored_image else None,
        }

    def _list_database_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        SessionLocal, Category, Product = self._database_dependencies()
        db = SessionLocal()
        try:
            query = db.query(Product).join(Category)
            if category is not None:
                query = query.filter(Category.slug == category.strip().lower())
            return [self._product_from_database(product) for product in query.all()]
        finally:
            db.close()

    def list_products(self) -> List[Dict[str, Any]]:
        products = deepcopy(PRODUCT_CATALOG)
        existing_ids = {str(product.get("id")) for product in products}
        products.extend(
            product
            for product in self._list_database_products()
            if str(product.get("id")) not in existing_ids
        )
        return products

    def list_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        key = (category or "").strip().lower()
        products = [
            deepcopy(item)
            for item in PRODUCT_CATALOG
            if item.get("category", "").lower() == key and item.get("status", "available") != "hidden" and item.get("is_active", True) is not False
        ]
        existing_ids = {str(product.get("id")) for product in products}
        products.extend(
            product
            for product in self._list_database_products(key)
            if str(product.get("id")) not in existing_ids
            and product.get("status", "available") != "hidden"
            and product.get("is_active", True) is not False
        )
        return products

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        for item in PRODUCT_CATALOG:
            if str(item.get("id")) == str(product_id):
                return deepcopy(item)
        try:
            numeric_id = int(product_id)
        except (TypeError, ValueError):
            return None

        SessionLocal, _, Product = self._database_dependencies()
        db = SessionLocal()
        try:
            product = db.get(Product, numeric_id)
            return self._product_from_database(product) if product else None
        finally:
            db.close()

    def get_stock(self, product_id: str, size: Optional[str] = None) -> int:
        product = self.get_product(product_id)
        if not product:
            return 0
        if product.get("sizes") and size:
            return int(product.get("stock_quantity", 0))
        return int(product.get("stock_quantity", 0))

    def validate_stock(self, product_id: str, quantity: int = 1, size: Optional[str] = None) -> bool:
        product = self.get_product(product_id)
        if not product:
            return False
        available = int(product.get("stock_quantity", 0))
        return available >= int(quantity)

    def reserve_stock(self, product_id: str, quantity: int = 1, size: Optional[str] = None) -> bool:
        if not self.validate_stock(product_id, quantity, size):
            return False

        for product in PRODUCT_CATALOG:
            if str(product.get("id")) == str(product_id):
                product["stock_quantity"] = int(product.get("stock_quantity", 0)) - int(quantity)
                return True
        return False

    def reserve_items(self, items: List[Dict[str, Any]]) -> bool:
        quantities: Dict[str, int] = {}
        for item in items:
            product_id = str(item.get("product_id") or item.get("id") or "")
            quantity = int(item.get("quantity", 1))
            if not product_id or quantity <= 0:
                raise ValueError("Reservation contains an invalid product or quantity.")
            quantities[product_id] = quantities.get(product_id, 0) + quantity

        catalog_products = {str(product.get("id")): product for product in PRODUCT_CATALOG}
        SessionLocal, _, Product = self._database_dependencies()
        db = SessionLocal()
        catalog_decrements: Dict[str, int] = {}
        try:
            for product_id, quantity in quantities.items():
                try:
                    database_id = int(product_id)
                except ValueError:
                    database_id = None

                database_product = db.get(Product, database_id) if database_id is not None else None
                if database_product is not None:
                    available = int(database_product.stock_quantity or 0)
                    if available < quantity:
                        raise ValueError(f"Not enough stock for {database_product.name}.")
                    database_product.stock_quantity = available - quantity
                    if product_id in catalog_products:
                        catalog_decrements[product_id] = quantity
                    continue

                catalog_product = catalog_products.get(product_id)
                if catalog_product is None:
                    raise ValueError(f"Product {product_id} was not found.")
                available = int(catalog_product.get("stock_quantity", 0))
                if available < quantity:
                    raise ValueError(f"Not enough stock for {catalog_product.get('name', product_id)}.")
                catalog_decrements[product_id] = quantity

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        for product_id, quantity in catalog_decrements.items():
            product = catalog_products[product_id]
            product["stock_quantity"] = int(product.get("stock_quantity", 0)) - quantity
        return True

    def add_product(self, product: Dict[str, Any], persist: bool = False) -> Dict[str, Any]:
        new_product = deepcopy(product)
        new_product.setdefault("id", f"product-{len(PRODUCT_CATALOG) + 1}")
        new_product.setdefault("category", "electronics")
        new_product.setdefault("sizes", [])
        new_product.setdefault("colors", [])
        new_product.setdefault("status", "available")
        new_product.setdefault("is_active", True)
        if "image_url" not in new_product and new_product.get("image_file_id"):
            new_product["image_url"] = new_product["image_file_id"]
        if "name_am" not in new_product:
            new_product["name_am"] = new_product.get("name", "Product")
        if "description_am" not in new_product:
            new_product["description_am"] = new_product.get("description", "")
        if persist:
            SessionLocal, Category, Product = self._database_dependencies()
            db = SessionLocal()
            try:
                category_slug = str(new_product["category"]).strip().lower()
                category = db.query(Category).filter(Category.slug == category_slug).first()
                if category is None:
                    category = Category(name=category_slug.title(), slug=category_slug)
                    db.add(category)
                    db.flush()

                image_file_id = new_product.get("image_file_id") or new_product.get("image_url")
                if image_file_id and new_product.get("image_source_type") == "document":
                    image_file_id = f"document:{image_file_id}"
                database_product = Product(
                    category_id=category.id,
                    name=new_product["name"],
                    name_am=new_product.get("name_am"),
                    description=new_product.get("description", ""),
                    description_am=new_product.get("description_am", ""),
                    price=float(new_product.get("price", 0)),
                    stock_quantity=int(new_product.get("stock_quantity", new_product.get("stock", 0))),
                    status=new_product.get("status", "available"),
                    image_file_id=image_file_id,
                )
                db.add(database_product)
                db.commit()
                db.refresh(database_product)
                new_product["id"] = str(database_product.id)
            finally:
                db.close()
        PRODUCT_CATALOG.append(new_product)
        return deepcopy(new_product)

    def update_product(self, product_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        updated_product = None
        for product in PRODUCT_CATALOG:
            if str(product.get("id")) == str(product_id):
                for key, value in updates.items():
                    if key == "stock":
                        product["stock_quantity"] = int(value)
                    elif key == "stock_quantity":
                        product["stock_quantity"] = int(value)
                    else:
                        product[key] = value
                updated_product = deepcopy(product)
                break

        try:
            numeric_id = int(product_id)
        except (TypeError, ValueError):
            if updated_product is not None:
                return updated_product
            raise ValueError(f"Product {product_id} not found")

        SessionLocal, Category, Product = self._database_dependencies()
        db = SessionLocal()
        try:
            database_product = db.get(Product, numeric_id)
            if database_product is not None:
                for key, value in updates.items():
                    if key in {"stock", "stock_quantity"}:
                        database_product.stock_quantity = int(value)
                    elif key == "category":
                        category_slug = str(value).strip().lower()
                        category = db.query(Category).filter(Category.slug == category_slug).first()
                        if category is None:
                            category = Category(name=category_slug.title(), slug=category_slug)
                            db.add(category)
                            db.flush()
                        database_product.category_id = category.id
                    elif hasattr(database_product, key):
                        setattr(database_product, key, value)
                db.commit()
                db.refresh(database_product)
                return self._product_from_database(database_product)
        finally:
            db.close()

        if updated_product is not None:
            return updated_product
        raise ValueError(f"Product {product_id} not found")

    def delete_product(self, product_id: str) -> bool:
        deleted_from_catalog = False
        for index, product in enumerate(PRODUCT_CATALOG):
            if str(product.get("id")) == str(product_id):
                PRODUCT_CATALOG.pop(index)
                deleted_from_catalog = True
                break

        try:
            numeric_id = int(product_id)
        except (TypeError, ValueError):
            return deleted_from_catalog

        SessionLocal, _, Product = self._database_dependencies()
        db = SessionLocal()
        try:
            database_product = db.get(Product, numeric_id)
            if database_product is None:
                return deleted_from_catalog
            db.delete(database_product)
            db.commit()
            return True
        finally:
            db.close()
