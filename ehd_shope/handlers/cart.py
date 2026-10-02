from __future__ import annotations

from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

try:
    from ehd_shope.handlers.message_utils import edit_callback_message
    from ehd_shope.services.order_service import OrderService
except ImportError:
    from handlers.message_utils import edit_callback_message
    from services.order_service import OrderService


def get_cart_keyboard(cart: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    for item in cart:
        key = item.get("item_key") or f"{item.get('product_id')}|default|default"
        rows.append([
            InlineKeyboardButton(f"➕ {item.get('name', 'Product')}", callback_data=f"cart:increase:{key}"),
            InlineKeyboardButton(f"➖ {item.get('quantity', 1)}", callback_data=f"cart:decrease:{key}"),
            InlineKeyboardButton("❌ Remove", callback_data=f"cart:remove:{key}"),
        ])

    rows.append([
        InlineKeyboardButton("💳 Telebirr", callback_data="payment:Telebirr|full_payment"),
        InlineKeyboardButton("🏦 CBE Birr", callback_data="payment:CBE|full_payment"),
    ])
    rows.append([
        InlineKeyboardButton("🔒 Reserve 50% · Telebirr", callback_data="payment:Telebirr|reservation"),
        InlineKeyboardButton("🔒 Reserve 50% · CBE", callback_data="payment:CBE|reservation"),
    ])
    rows.append([
        InlineKeyboardButton("🧾 Order / ትዕዛዝ ይስጡ", callback_data="checkout"),
        InlineKeyboardButton("🏠 Home / መነሻ", callback_data="home"),
    ])
    return InlineKeyboardMarkup(rows)


async def cart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cart = context.user_data.get("cart", [])
    if not cart:
        await update.message.reply_text("Your cart is empty. / ጋሪዎ ባዶ ነው።")
        return

    current_order = OrderService().build_cart_payment_state(
        telegram_id=update.effective_user.id if update.effective_user else 0,
        cart=cart,
        order_type="full_payment",
    )
    context.user_data["current_order"] = current_order
    context.user_data["cart_total"] = current_order["total_price"]

    total = current_order["total_price"]
    text = "🛒 YOUR CART / የእርስዎ ጋሪ\n\n"
    text += "Choose your payment method below / የክፍያ አማራጭ ከዚህ በታች ይምረጡ\n\n"
    for item in cart:
        text += (
            f"{item['name']}\n"
            f"Quantity: {item['quantity']}\n"
            f"Price: {float(item['price']):,.0f} ETB\n"
            f"Subtotal: {float(item['price']) * int(item['quantity']):,.0f} ETB\n\n"
        )
    text += f"TOTAL: {total:,.0f} ETB"
    await update.message.reply_text(text, reply_markup=get_cart_keyboard(cart))


async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cart = context.user_data.get("cart", [])
    query = update.callback_query
    if not cart:
        if query:
            await query.answer()
            await edit_callback_message(
                update,
                "Your cart is empty. / ጋሪዎ ባዶ ነው።",
                get_cart_keyboard([]),
            )
        return

    current_order = OrderService().build_cart_payment_state(
        telegram_id=update.effective_user.id if update.effective_user else 0,
        cart=cart,
        order_type="full_payment",
    )
    context.user_data["current_order"] = current_order
    context.user_data["cart_total"] = current_order["total_price"]

    total = current_order["total_price"]
    text = "🛒 YOUR CART / የእርስዎ ጋሪ\n\n"
    text += "Choose your payment method below / የክፍያ አማራጭ ከዚህ በታች ይምረጡ\n\n"
    for item in cart:
        text += (
            f"{item['name']}\n"
            f"Quantity: {item['quantity']}\n"
            f"Price: {float(item['price']):,.0f} ETB\n"
            f"Subtotal: {float(item['price']) * int(item['quantity']):,.0f} ETB\n\n"
        )
    text += f"TOTAL: {total:,.0f} ETB"
    if query:
        await query.answer()
        await edit_callback_message(update, text, get_cart_keyboard(cart))
    else:
        await update.message.reply_text(text, reply_markup=get_cart_keyboard(cart))


async def handle_cart_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    cart = context.user_data.setdefault("cart", [])
    command, _, item_key = action.partition(":")

    if command == "increase":
        for item in cart:
            if item.get("item_key") == item_key:
                item["quantity"] = int(item.get("quantity", 1)) + 1
        current_order = OrderService().build_cart_payment_state(
            telegram_id=update.effective_user.id if update.effective_user else 0,
            cart=cart,
            order_type="full_payment",
        )
        context.user_data["current_order"] = current_order
        context.user_data["cart_total"] = current_order["total_price"]
        await show_cart(update, context)
        return

    if command == "decrease":
        for item in cart:
            if item.get("item_key") == item_key:
                new_quantity = int(item.get("quantity", 1)) - 1
                if new_quantity <= 0:
                    cart.remove(item)
                else:
                    item["quantity"] = new_quantity
        current_order = OrderService().build_cart_payment_state(
            telegram_id=update.effective_user.id if update.effective_user else 0,
            cart=cart,
            order_type="full_payment",
        )
        context.user_data["current_order"] = current_order
        context.user_data["cart_total"] = current_order["total_price"]
        await show_cart(update, context)
        return

    if command == "remove":
        for item in list(cart):
            if item.get("item_key") == item_key:
                cart.remove(item)
        current_order = OrderService().build_cart_payment_state(
            telegram_id=update.effective_user.id if update.effective_user else 0,
            cart=cart,
            order_type="full_payment",
        )
        context.user_data["current_order"] = current_order
        context.user_data["cart_total"] = current_order["total_price"]
        await show_cart(update, context)
        return

    if update.callback_query:
        await update.callback_query.answer("Unsupported cart action.", show_alert=True)


def handle_cart() -> str:
    return "Cart placeholder."
