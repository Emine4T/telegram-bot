import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
TELEGRAM_BOT_TOKEN = BOT_TOKEN
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", str(ADMIN_ID)).split(",") if x.strip()]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ehd_shop.db'}")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "test")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
UPLOADS_DIR = BASE_DIR / "uploads" / "receipts"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
