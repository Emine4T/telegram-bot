from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

try:
    from ehd_shope.handlers.message_utils import edit_callback_message
    from ehd_shope.services.order_service import OrderService
except ImportError:
    from handlers.message_utils import edit_callback_message
    from services.order_service import OrderService


def get_payment_method_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Telebirr", callback_data="payment:Telebirr|full_payment")],
        [InlineKeyboardButton("🏦 CBE Birr", callback_data="payment:CBE|full_payment")],
        [InlineKeyboardButton("🔒 Reserve with 50% · Telebirr", callback_data="payment:Telebirr|reservation")],
        [InlineKeyboardButton("🔒 Reserve with 50% · CBE", callback_data="payment:CBE|reservation")],
    ])


def build_order_summary_text(cart) -> str:
    summary = OrderService().build_order_summary(cart)
    lines = [
        "ORDER SUMMARY / የትዕዛዝ ማጠቃለያ",
        "",
    ]
    for item in summary["items"]:
        lines.append(f"Product: {item['name']}\nQuantity: {item['quantity']}\nPrice: {float(item['price']):,.0f} ETB")
        lines.append("")
    lines.append(f"TOTAL: {summary['total']:,.0f} ETB")
    return "\n".join(lines)


async def checkout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cart = context.user_data.get("cart", [])
    if not cart:
        await update.message.reply_text("Your cart is empty. Add products before checkout. / ጋሪዎ ባዶ ነው።")
        return

    context.user_data["current_order"] = OrderService().build_cart_payment_state(
        telegram_id=update.effective_user.id if update.effective_user else 0,
        cart=cart,
        order_type="full_payment",
    )
    summary = build_order_summary_text(cart)
    await update.message.reply_text(summary, reply_markup=get_payment_method_keyboard())


async def start_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cart = context.user_data.get("cart", [])
    if not cart:
        await update.callback_query.answer("Your cart is empty.", show_alert=True)
        return

    context.user_data["current_order"] = OrderService().build_cart_payment_state(
        telegram_id=update.effective_user.id if update.effective_user else 0,
        cart=cart,
        order_type="full_payment",
    )
    summary = build_order_summary_text(cart)
    await update.callback_query.answer()
    await edit_callback_message(update, summary, get_payment_method_keyboard())


def handle_checkout() -> str:
    return "Checkout placeholder."
