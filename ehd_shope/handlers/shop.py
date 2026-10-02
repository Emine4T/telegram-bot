from __future__ import annotations

import logging
from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

try:
    from ehd_shope.handlers.message_utils import edit_callback_message
    from ehd_shope.services.inventory_service import InventoryService
    from ehd_shope.services.order_service import OrderService
except ImportError:
    from handlers.message_utils import edit_callback_message
    from services.inventory_service import InventoryService
    from services.order_service import OrderService

logger = logging.getLogger(__name__)


def can_edit_message_caption(message: Any) -> bool:
    return bool(getattr(message, "photo", None))


async def edit_navigation_message(update: Update, text: str, reply_markup: InlineKeyboardMarkup, parse_mode: str | None = None) -> None:
    await edit_callback_message(update, text, reply_markup, parse_mode=parse_mode)


CATEGORY_LABELS = {
    "electronics": {"en": "Electronics / ኤሌክትሮኒክስ", "am": "ኤሌክትሮኒክስ / Electronics"},
    "shoes": {"en": "Shoes / ጫማ", "am": "ጫማ / Shoes"},
    "clothes": {"en": "Clothes / ልብስ", "am": "ልብስ / Clothes"},
    "drugstore": {"en": "Drugstore / መድኃኒት ቤት", "am": "መድኃኒት ቤት / Drugstore"},
}


def get_cart_button_text(cart: List[Dict[str, Any]]) -> str:
    return f"🛒 Cart ({len(cart)})"


def get_category_keyboard(category: str, cart: List[Dict[str, Any]], language: str = "en") -> InlineKeyboardMarkup:
    products = InventoryService().list_products_by_category(category)
    rows: List[List[InlineKeyboardButton]] = []

    for product in products:
        rows.append([
            InlineKeyboardButton(
                f"{product.get('name', 'Product')} - {float(product.get('price', 0)):,.0f} ETB",
                callback_data=f"product:{product.get('id')}",
            )
        ])

    rows.append([
        InlineKeyboardButton("🏠 Home / መነሻ", callback_data="home"),
        InlineKeyboardButton(get_cart_button_text(cart), callback_data="show_cart"),
    ])
    return InlineKeyboardMarkup(rows)


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    category = context.user_data.get("selected_category") or "electronics"
    cart = context.user_data.get("cart", [])
    markup = get_category_keyboard(category, cart, context.user_data.get("language", "en"))
    text = "Select a category / ምድብ ይምረጡ"
    if not InventoryService().list_products_by_category(category):
        text = "No products yet in this category. / በዚህ ምድብ ውስጥ ምርቶች የሉም።"
    if update.message:
        await update.message.reply_text(text, reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=markup)


async def show_category(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    category: str,
    callback_answer: str = "",
) -> None:
    context.user_data["selected_category"] = category
    cart = context.user_data.get("cart", [])
    markup = get_category_keyboard(category, cart, context.user_data.get("language", "en"))
    text = CATEGORY_LABELS.get(category, {}).get(context.user_data.get("language", "en"), category.title())
    if not InventoryService().list_products_by_category(category):
        text += "\n\nNo products yet in this category. / በዚህ ምድብ ውስጥ ምርቶች የሉም።"

    query = update.callback_query
    if query:
        await query.answer(callback_answer)
        await edit_navigation_message(update, text, markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def show_product_card(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str) -> None:
    product = InventoryService().get_product(product_id)
    if not product:
        if update.callback_query:
            await update.callback_query.answer("Product not found.", show_alert=True)
        return

    image_ref = product.get("image_file_id") or product.get("image_url")
    image_source_type = product.get("image_source_type")
    name = product.get("name", "Product")
    name_am = product.get("name_am", "")
    description = product.get("description", "No description available.")
    description_am = product.get("description_am", "")
    details = product.get("details") or product.get("admin_notes") or ""
    price = float(product.get("price", 0))
    stock = int(product.get("stock_quantity", 0))

    detail_block = ""
    if details:
        detail_block = f"\n📌 Admin details: {details}"

    caption = (
        f"📱 <b>{name}</b>\n"
        f"{name_am}\n\n"
        f"💰 <b>{price:,.0f} ETB</b>\n"
        f"📦 Stock: {stock} available\n\n"
        f"{description}\n"
        f"{description_am}{detail_block}"
    )

    buttons: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("🛒 Add to Cart / ወደ ጋሪ ጨምር", callback_data=f"add_to_cart:{product_id}"),
        ]
    ]

    buttons.append([
        InlineKeyboardButton("⬅️ Back / ተመለስ", callback_data=f"category:{product.get('category', 'electronics')}"),
        InlineKeyboardButton("🏠 Home / መነሻ", callback_data="home"),
    ])

    callback_answered = False
    if image_ref and update.callback_query:
        try:
            await update.callback_query.answer()
            callback_answered = True
            chat = update.callback_query.message.chat
            image_data = None
            if image_source_type == "document":
                telegram_file = await context.bot.get_file(image_ref)
                image_data = bytes(await telegram_file.download_as_bytearray())
            try:
                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=image_data or image_ref,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML",
                )
            except BadRequest:
                if image_data is not None:
                    raise
                telegram_file = await context.bot.get_file(image_ref)
                image_data = bytes(await telegram_file.download_as_bytearray())
                await context.bot.send_photo(
                    chat_id=chat.id,
                    photo=image_data,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode="HTML",
                )
            return
        except Exception:
            logger.exception("Unable to display product image for %s", product_id)

    if update.callback_query:
        if not callback_answered:
            await update.callback_query.answer()
        await edit_navigation_message(
            update,
            caption,
            InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )
    elif update.message:
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")


async def handle_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str) -> None:
    cart = context.user_data.setdefault("cart", [])
    product = InventoryService().get_product(product_id)
    if not product:
        if update.callback_query:
            await update.callback_query.answer("Product not found.", show_alert=True)
        return

    item_key = f"{product_id}|default|default"
    existing = next((item for item in cart if item.get("item_key") == item_key), None)

    if existing is None:
        cart.append(
            {
                "product_id": product_id,
                "item_key": item_key,
                "name": product["name"],
                "price": float(product["price"]),
                "quantity": 1,
                "size": None,
                "color": None,
            }
        )
    else:
        existing["quantity"] = int(existing.get("quantity", 1)) + 1

    telegram_id = update.effective_user.id if update.effective_user else 0
    context.user_data["current_order"] = OrderService().build_cart_payment_state(
        telegram_id=telegram_id,
        cart=cart,
        order_type="full_payment",
    )

    category = context.user_data.get("selected_category") or product.get("category", "electronics")
    await show_category(update, context, category, callback_answer="✅ Product added to your cart.")


def handle_shop() -> str:
    return "Shop menu placeholder."
