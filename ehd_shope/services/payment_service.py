from typing import Any, Dict

from database.database import get_db


class PaymentService:
    def __init__(self) -> None:
        self.db = get_db()

    def process_payment(self, order_id: str, provider: str = "test") -> Dict[str, Any]:
        if provider == "test":
            self.db.orders.update_one({"_id": order_id}, {"$set": {"payment_status": "paid", "status": "paid"}})
            return {"status": "success", "provider": provider, "order_id": order_id}

        return {"status": "not_supported", "provider": provider, "order_id": order_id}
