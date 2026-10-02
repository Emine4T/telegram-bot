import logging
from typing import Any, Literal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

try:
    from ehd_shope.handlers.message_utils import edit_callback_message
    from ehd_shope.database.database import SessionLocal
    from ehd_shope.database.models import User
    from ehd_shope.services.order_service import OrderService
except ImportError:
    from handlers.message_utils import edit_callback_message
    from database.database import SessionLocal
    from database.models import User
    from services.order_service import OrderService


def can_edit_message_caption(message: Any) -> bool:
    return bool(getattr(message, "photo", None))


async def edit_home_message(update: Update, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    await edit_callback_message(update, text, reply_markup)

Language = Literal["en", "am"]


def build_start_message(language: Language = "en") -> str:
    english = (
        "👋 Welcome to our store!\n"
        "Browse our products, add your favorite items to your cart, and place your order easily."
    )
    amharic = (
        "👋 እንኳን ወደ ሱቃችን በደህና መጡ!\n"
        "የሚፈልጉትን ምርት ይምረጡ፣ ወደ ጋሪዎ ይጨምሩ እና ትዕዛዝዎን በቀላሉ ያስገቡ።"
    )

    if language == "am":
        return f"{amharic}\n\n{english}"

    return f"{english}\n\n{amharic}"


def build_home_keyboard(language: Language = "en") -> InlineKeyboardMarkup:
    if language == "am":
        buttons = [
            [InlineKeyboardButton("🛍 ኤሌክትሮኒክስ / Electronics", callback_data="category:electronics")],
            [InlineKeyboardButton("👟 ጫማ / Shoes", callback_data="category:shoes")],
            [InlineKeyboardButton("👕 ልብስ / Clothes", callback_data="category:clothes")],
            [InlineKeyboardButton("💊 መድኃኒት ቤት / Drugstore", callback_data="category:drugstore")],
            [InlineKeyboardButton("🛒 የእኔ ጋሪ / My Cart", callback_data="show_cart")],
            [InlineKeyboardButton("📦 የእኔ ትዕዛዞች / My Orders", callback_data="my_orders")],
            [InlineKeyboardButton("🌐 ቋንቋ / Language", callback_data="language")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton("🛍 Electronics / ኤሌክትሮኒክስ", callback_data="category:electronics")],
            [InlineKeyboardButton("👟 Shoes / ጫማ", callback_data="category:shoes")],
            [InlineKeyboardButton("👕 Clothes / ልብስ", callback_data="category:clothes")],
            [InlineKeyboardButton("💊 Drugstore / መድኃኒት ቤት", callback_data="category:drugstore")],
            [InlineKeyboardButton("🛒 My Cart / የእኔ ጋሪ", callback_data="show_cart")],
            [InlineKeyboardButton("📦 My Orders / የእኔ ትዕዛዞች", callback_data="my_orders")],
            [InlineKeyboardButton("🌐 Language / ቋንቋ", callback_data="language")],
        ]

    return InlineKeyboardMarkup(buttons)


def get_home_keyboard(language: Language = "en") -> InlineKeyboardMarkup:
    return build_home_keyboard(language)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("Unable to identify you.")
        return

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.telegram_id == user.id).first()
        if existing is None:
            db.add(
                User(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    language="en",
                )
            )
            db.commit()
            language = "en"
        else:
            language = existing.language or "en"
    except Exception:
        logging.exception("Could not create or load Telegram user while handling /start")
        language = "en"
    finally:
        db.close()

    if update.message:
        await update.message.reply_text(
            build_start_message(language),
            reply_markup=build_home_keyboard(language),
        )


async def my_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id if update.effective_user else 0
    orders = OrderService().get_orders_for_user(user_id)
    current_order = context.user_data.get("current_order")
    if current_order and not orders:
        orders = [current_order]

    if not orders:
        message = "You have no orders yet. / እስካሁን ትዕዛዝ የሎትም።"
        if update.callback_query:
            await update.callback_query.answer()
            await edit_callback_message(update, message, build_home_keyboard(context.user_data.get("language", "en")))
        elif update.message:
            await update.message.reply_text(message)
        return

    lines = ["📦 MY ORDERS / የእኔ ትዕዛዞች\n"]
    for index, order in enumerate(orders, start=1):
        total = float(order.get("total_price", order.get("amount_due", 0)) or 0)
        lines.append(f"{index}. Order {order.get('order_id', '#ORD')} - {total:,.0f} ETB")
    message = "\n".join(lines)

    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(update, message, build_home_keyboard(context.user_data.get("language", "en")))
    elif update.message:
        await update.message.reply_text(message, reply_markup=build_home_keyboard(context.user_data.get("language", "en")))


async def toggle_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current = context.user_data.get("language", "en")
    new_language = "am" if current == "en" else "en"
    context.user_data["language"] = new_language
    if update.callback_query:
        await update.callback_query.answer(f"Language set to {new_language}.")
        await edit_home_message(update, "🏠 HOME", build_home_keyboard(new_language))
        return
    await home_command(update, context)


async def home_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    language = context.user_data.get("language", "en")
    if update.callback_query:
        await update.callback_query.answer()
        await edit_home_message(update, "🏠 HOME", build_home_keyboard(language))
        return

    await update.message.reply_text("🏠 HOME", reply_markup=build_home_keyboard(language))
