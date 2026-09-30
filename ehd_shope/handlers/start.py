from telegram import Update
from telegram.ext import ContextTypes

from database.database import get_db
from database.models import User


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db = get_db()

    existing = db.users.find_one({"telegram_id": user.id})
    if not existing:
        db.users.insert_one(
            User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            ).to_dict()
        )

    await update.message.reply_text(
        "Welcome to EHD Shop!\n\n"
        "Use /auth to register and /help to see available commands."
    )
