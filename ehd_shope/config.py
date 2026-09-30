import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ehd_shop")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "test")
UPLOADS_DIR = BASE_DIR / "uploads" / "receipts"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
