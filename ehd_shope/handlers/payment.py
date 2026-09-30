from telegram import Update
from telegram.ext import ContextTypes


async def payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Payment instructions: send proof of payment after checkout.")


def handle_payment() -> str:
    return "Payment placeholder."
