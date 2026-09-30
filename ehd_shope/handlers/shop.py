from telegram import Update
from telegram.ext import ContextTypes

from services.inventory_service import InventoryService


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    products = InventoryService().list_products()
    if not products:
        await update.message.reply_text("No products available yet.")
        return

    lines = [f"{p['name']} - {p['price']} USD (stock: {p['stock']})" for p in products]
    await update.message.reply_text("\n".join(lines))


def handle_shop() -> str:
    return "Shop menu placeholder."
