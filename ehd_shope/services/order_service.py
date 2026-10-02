from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


class OrderService:
    _orders: List[Dict[str, Any]] = []

    def build_order_summary(self, cart: List[Dict[str, Any]]) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        total = 0.0

        for item in cart:
            quantity = int(item.get("quantity", 1))
            price = float(item.get("price", 0))
            subtotal = price * quantity
            total += subtotal
            items.append(
                {
                    "product_id": item.get("product_id") or item.get("id"),
                    "name": item.get("name", "Product"),
                    "quantity": quantity,
                    "price": price,
                    "subtotal": subtotal,
                    "size": item.get("size"),
                    "color": item.get("color"),
                }
            )

        return {"items": items, "total": total, "created_at": datetime.now(timezone.utc)}

    def build_cart_payment_state(self, telegram_id: int, cart: List[Dict[str, Any]], order_type: str = "full_payment") -> Dict[str, Any]:
        summary = self.build_order_summary(cart)
        normalized_type = (order_type or "full_payment").lower()
        breakdown = self.get_payment_breakdown(summary["total"], normalized_type)
        return {
            "telegram_id": telegram_id,
            "order_type": normalized_type,
            "items": summary["items"],
            "total_price": summary["total"],
            "deposit_amount": breakdown["deposit_amount"],
            "remaining_balance": breakdown["remaining_balance"],
            "amount_due": breakdown["amount_due"],
            "payment_status": "pending",
            "order_status": "awaiting_payment",
            "created_at": datetime.now(timezone.utc),
        }

    def get_payment_breakdown(self, total_price: float, order_type: str = "full_payment") -> Dict[str, float]:
        normalized_type = (order_type or "full_payment").lower()
        if normalized_type == "reservation":
            deposit = float(total_price) * 0.5
            remaining = float(total_price) - deposit
            return {"deposit_amount": deposit, "remaining_balance": remaining, "amount_due": deposit}
        return {"deposit_amount": 0.0, "remaining_balance": 0.0, "amount_due": float(total_price)}

    def create_order(self, telegram_id: int, cart: List[Dict[str, Any]], order_type: str = "full_payment") -> Dict[str, Any]:
        summary = self.build_order_summary(cart)
        normalized_type = (order_type or "full_payment").lower()
        breakdown = self.get_payment_breakdown(summary["total"], normalized_type)
        order = {
            "telegram_id": telegram_id,
            "order_id": f"#ORD-{uuid4().hex[:10].upper()}",
            "order_type": normalized_type,
            "items": summary["items"],
            "total_price": summary["total"],
            "deposit_amount": breakdown["deposit_amount"],
            "remaining_balance": breakdown["remaining_balance"],
            "amount_due": breakdown["amount_due"],
            "payment_status": "pending",
            "order_status": "awaiting_payment",
            "created_at": datetime.now(timezone.utc),
        }
        self._orders.append(order)
        return order

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        for order in self._orders:
            if str(order.get("order_id")) == str(order_id):
                return order
        return None

    def update_order_status(self, order_id: str, status: str, payment_status: Optional[str] = None) -> Dict[str, Any]:
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"No order found for order {order_id}")
        order["order_status"] = status
        if payment_status is not None:
            order["payment_status"] = payment_status
        order["updated_at"] = datetime.now(timezone.utc)
        return order

    def get_orders_for_user(self, telegram_id: int):
        return [order for order in self._orders if int(order.get("telegram_id", 0)) == int(telegram_id)]

    def get_reserved_orders(self) -> List[Dict[str, Any]]:
        return [
            order for order in self._orders
            if str(order.get("order_status", "")).lower() == "reserved"
        ]

    def get_reserved_product_summary(self) -> List[Dict[str, Any]]:
        reserved: List[Dict[str, Any]] = []
        for order in self.get_reserved_orders():
            items = order.get("items", [])
            product_names = ", ".join(item.get("name", "Product") for item in items) or "Unknown product"
            reserved.append({
                "order_id": order.get("order_id"),
                "customer_id": order.get("telegram_id"),
                "products": product_names,
                "amount_due": order.get("amount_due", order.get("total_price", 0)),
            })
        return reserved
