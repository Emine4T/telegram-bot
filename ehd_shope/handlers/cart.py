from telegram import Update
from telegram.ext import ContextTypes


async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Cart is empty for now.")


def handle_cart() -> str:
    return "Cart placeholder."
