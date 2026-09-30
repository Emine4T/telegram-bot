from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from handlers.admin import admin_command
from handlers.auth import auth_command
from handlers.cart import cart_command
from handlers.checkout import checkout_command
from handlers.payment import payment_command
from handlers.shop import shop_command
from handlers.start import start_command
from handlers.support import support_command

load_dotenv()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/start - welcome message\n"
        "/auth - register account\n"
        "/shop - view products\n"
        "/cart - view cart\n"
        "/checkout - start checkout\n"
        "/payment - payment instructions\n"
        "/support - support info\n"
        "/admin - admin panel"
    )


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("auth", auth_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("cart", cart_command))
    application.add_handler(CommandHandler("checkout", checkout_command))
    application.add_handler(CommandHandler("payment", payment_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("help", help_command))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # type: ignore[attr-defined]
    print("EHD Shop bot is running...")
    await application.updater.idle()  # type: ignore[attr-defined]


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
