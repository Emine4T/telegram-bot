from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=True)

    def __init__(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_admin: bool = False,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.is_admin = is_admin
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    def __init__(
        self,
        name: str,
        description: str,
        price: float,
        stock: int,
        is_active: bool = True,
    ) -> None:
        self.name = name
        self.description = description
        self.price = price
        self.stock = stock
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "stock": self.stock,
            "is_active": self.is_active,
        }


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User")
    product = relationship("Product")

    def __init__(self, telegram_id: int, product_id: str, quantity: int = 1) -> None:
        self.telegram_id = telegram_id
        self.product_id = product_id
        self.quantity = quantity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telegram_id": self.telegram_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
        }


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String, default="pending")
    payment_status = Column(String, default="unpaid")
    created_at = Column(DateTime, nullable=True)

    user = relationship("User")

    def __init__(
        self,
        telegram_id: int,
        items: List[Dict[str, Any]],
        total_amount: float,
        status: str = "pending",
        payment_status: str = "unpaid",
    ) -> None:
        self.telegram_id = telegram_id
        self.items = items
        self.total_amount = total_amount
        self.status = status
        self.payment_status = payment_status
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telegram_id": self.telegram_id,
            "items": self.items,
            "total_amount": self.total_amount,
            "status": self.status,
            "payment_status": self.payment_status,
            "created_at": self.created_at,
        }


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)

    order = relationship("Order")
    product = relationship("Product")


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=True)

    order = relationship("Order")

    def __init__(self, order_id: str, file_path: str) -> None:
        self.order_id = order_id
        self.file_path = file_path
        self.uploaded_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "file_path": self.file_path,
            "uploaded_at": self.uploaded_at,
        }
