from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from ehd_shope.services.inventory_service import InventoryService
    from ehd_shope.services.order_service import OrderService
except ImportError:
    from services.inventory_service import InventoryService
    from services.order_service import OrderService


class PaymentService:
    _submissions: List[Dict[str, Any]] = []
    _setting_prefix = "payment_review:"

    @staticmethod
    def _database_dependencies():
        try:
            from ehd_shope.database.database import SessionLocal
            from ehd_shope.database.models import StoreSetting
        except ImportError:
            from database.database import SessionLocal
            from database.models import StoreSetting
        return SessionLocal, StoreSetting

    def _load_persisted(self, order_id: str) -> Optional[Dict[str, Any]]:
        SessionLocal, StoreSetting = self._database_dependencies()
        db = SessionLocal()
        try:
            setting = db.query(StoreSetting).filter(
                StoreSetting.key == f"{self._setting_prefix}{order_id}"
            ).first()
            if setting is None:
                return None
            submission = json.loads(setting.value)
            submission["_persistent"] = True
            return submission
        finally:
            db.close()

    def _list_persisted(self) -> List[Dict[str, Any]]:
        SessionLocal, StoreSetting = self._database_dependencies()
        db = SessionLocal()
        try:
            settings = db.query(StoreSetting).filter(
                StoreSetting.key.like(f"{self._setting_prefix}%")
            ).all()
            submissions = []
            for setting in settings:
                submission = json.loads(setting.value)
                submission["_persistent"] = True
                submissions.append(submission)
            return submissions
        finally:
            db.close()

    def _save_persisted(self, submission: Dict[str, Any]) -> None:
        SessionLocal, StoreSetting = self._database_dependencies()
        db = SessionLocal()
        try:
            key = f"{self._setting_prefix}{submission['order_id']}"
            setting = db.query(StoreSetting).filter(StoreSetting.key == key).first()
            value = json.dumps(
                {key: value for key, value in submission.items() if key != "_persistent"},
                default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value),
            )
            if setting is None:
                setting = StoreSetting(key=key, value=value, description="Payment review state")
                db.add(setting)
            else:
                setting.value = value
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def submit_payment(
        self,
        order_id: str,
        customer_id: int,
        payment_method: str,
        payment_type: str,
        amount: float,
        transaction_number: Optional[str] = None,
        screenshot_file_id: Optional[str] = None,
        order_data: Optional[Dict[str, Any]] = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        existing = self.get_submission(order_id)
        if existing:
            return existing

        submission = {
            "order_id": order_id,
            "customer_id": customer_id,
            "payment_method": payment_method,
            "payment_type": payment_type,
            "amount": float(amount),
            "transaction_number": transaction_number,
            "screenshot_file_id": screenshot_file_id,
            "status": "pending",
            "order_status": "awaiting_payment",
            "submitted_at": datetime.now(timezone.utc),
            "order_data": order_data,
            "_persistent": persist,
        }
        self._submissions.append(submission)
        if persist:
            self._save_persisted(submission)
        return submission

    def get_submission(self, order_id: str) -> Optional[Dict[str, Any]]:
        persisted = self._load_persisted(order_id)
        if persisted is not None:
            return persisted
        for item in self._submissions:
            if item.get("order_id") == order_id:
                return item
        return None

    def list_pending(self) -> List[Dict[str, Any]]:
        submissions = {item["order_id"]: item for item in self._submissions}
        submissions.update({item["order_id"]: item for item in self._list_persisted()})
        return [item for item in submissions.values() if item.get("status") == "pending"]

    def approve_payment(self, order_id: str) -> Dict[str, Any]:
        item = self.get_submission(order_id)
        if item is None:
            raise ValueError(f"No payment submission found for order {order_id}")
        if item.get("status") != "pending":
            raise ValueError(f"Payment for order {order_id} is no longer pending")

        order = OrderService().get_order(order_id) or item.get("order_data")
        payment_type = str(item.get("payment_type", "full_payment")).lower()
        if payment_type == "reservation":
            if order is None:
                raise ValueError(f"Order {order_id} could not be found for stock reservation.")
            InventoryService().reserve_items(order.get("items", []))
        item["status"] = "approved"
        item["updated_at"] = datetime.now(timezone.utc)
        item["order_status"] = "paid" if payment_type == "full_payment" else "reserved"
        try:
            OrderService().update_order_status(order_id, item["order_status"], payment_status="approved")
        except ValueError:
            pass
        if item.get("_persistent"):
            self._save_persisted(item)
        return item

    def reject_payment(self, order_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        item = self.get_submission(order_id)
        if item is None:
            raise ValueError(f"No payment submission found for order {order_id}")
        if item.get("status") != "pending":
            raise ValueError(f"Payment for order {order_id} is no longer pending")
        item["status"] = "rejected"
        item["reason"] = reason or "Payment verification failed"
        item["updated_at"] = datetime.now(timezone.utc)
        item["order_status"] = "payment_failed"
        try:
            OrderService().update_order_status(order_id, "payment_failed", payment_status="rejected")
        except ValueError:
            pass
        if item.get("_persistent"):
            self._save_persisted(item)
        return item

    def process_payment(self, order_id: str, provider: str = "test") -> Dict[str, Any]:
        submission = self.get_submission(order_id)
        if not submission:
            return {"status": "not_found", "provider": provider, "order_id": order_id}
        return {"status": submission.get("status", "pending"), "provider": provider, "order_id": order_id}
