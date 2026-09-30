from datetime import datetime
from typing import Any, Dict, List

from database.database import get_db


class OrderService:
    def __init__(self) -> None:
        self.db = get_db()

    def create_order(self, telegram_id: int, items: List[Dict[str, Any]], total_amount: float) -> Dict[str, Any]:
        order = {
            "telegram_id": telegram_id,
            "items": items,
            "total_amount": total_amount,
            "status": "pending",
            "payment_status": "unpaid",
            "created_at": datetime.utcnow(),
        }
        result = self.db.orders.insert_one(order)
        order["_id"] = result.inserted_id
        return order

    def get_orders_for_user(self, telegram_id: int):
        return list(self.db.orders.find({"telegram_id": telegram_id}))
