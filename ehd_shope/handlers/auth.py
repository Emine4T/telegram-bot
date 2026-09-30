from telegram import Update
from telegram.ext import ContextTypes

from database.database import get_db
from database.models import User


async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db = get_db()

    if not user:
        await update.message.reply_text("Unable to identify you.")
        return

    record = db.users.find_one({"telegram_id": user.id})
    if not record:
        db.users.insert_one(
            User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            ).to_dict()
        )
        await update.message.reply_text("You are now registered in EHD Shop.")
        return

    db.users.update_one({"telegram_id": user.id}, {"$set": {"is_active": True}})
    await update.message.reply_text("Your account is already active.")


def handle_auth() -> str:
    return "Authentication flow placeholder."
