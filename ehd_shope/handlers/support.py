from telegram import Update
from telegram.ext import ContextTypes


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Support contact: hello@ehdshop.example")


def handle_support() -> str:
    return "Support contact placeholder."
