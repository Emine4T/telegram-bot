from pymongo import MongoClient
from pymongo.database import Database

from config import MONGO_DB_NAME, MONGO_URI

client = MongoClient(MONGO_URI)
db: Database = client[MONGO_DB_NAME]


def get_db() -> Database:
    return db


def ensure_indexes() -> None:
    db.users.create_index("telegram_id", unique=True)
    db.users.create_index("username")
    db.products.create_index("name")
    db.orders.create_index("user_id")
    db.carts.create_index([("telegram_id", 1), ("product_id", 1)], unique=True)
