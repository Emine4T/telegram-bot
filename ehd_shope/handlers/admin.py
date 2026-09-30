from telegram import Update
from telegram.ext import ContextTypes


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Admin panel is ready for management actions.")
