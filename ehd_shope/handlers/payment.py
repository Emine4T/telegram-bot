import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

try:
    from ehd_shope.config import ADMIN_IDS
    from ehd_shope.handlers.admin import get_admin_review_keyboard
    from ehd_shope.handlers.message_utils import edit_callback_message
    from ehd_shope.services.order_service import OrderService
    from ehd_shope.services.payment_service import PaymentService
except ImportError:
    from config import ADMIN_IDS
    from handlers.admin import get_admin_review_keyboard
    from handlers.message_utils import edit_callback_message
    from services.order_service import OrderService
    from services.payment_service import PaymentService

logger = logging.getLogger(__name__)


def _parse_payment_choice(raw_choice: str) -> tuple[str, str]:
    value = (raw_choice or "").strip()
    if "|" in value:
        provider, payment_type = value.split("|", 1)
        return provider.strip(), (payment_type or "full_payment").strip().lower()
    if value.lower() == "reservation":
        return "Telebirr", "reservation"
    return value or "Telebirr", "full_payment"


def get_payment_instructions_keyboard(provider: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Upload Screenshot / የክፍያ ስክሪንሾት ይላኩ", callback_data=f"upload_receipt:{provider}")],
        [InlineKeyboardButton("🔢 Enter Transaction Number / የግብይት ቁጥር ያስገቡ", callback_data=f"enter_txn:{provider}")],
        [InlineKeyboardButton("🏠 Home / መነሻ", callback_data="home")],
    ])


async def payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Payment instructions: after checkout, choose a payment method and upload the proof of payment.\n\n"
        "የክፍያ መመሪያ: ከክፍያ በኋላ የክፍያ አማራጭ ይምረጡ እና የክፍያ ማረጋገጫ ይላኩ።"
    )


async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE, provider: str) -> None:
    provider_name, payment_type = _parse_payment_choice(provider)
    provider_name_upper = provider_name.upper()

    current_order = context.user_data.get("current_order") or {}
    if not current_order.get("order_id") or current_order.get("order_type") != payment_type:
        cart = context.user_data.get("cart", [])
        if not cart:
            if update.callback_query:
                await update.callback_query.answer("Your cart is empty.", show_alert=True)
            return
        order_service = OrderService()
        order = order_service.create_order(
            telegram_id=update.effective_user.id if update.effective_user else 0,
            cart=cart,
            order_type=payment_type,
        )
        current_order = {
            **order,
            **order_service.build_cart_payment_state(
                telegram_id=update.effective_user.id if update.effective_user else 0,
                cart=cart,
                order_type=payment_type,
            ),
        }
        context.user_data["current_order"] = current_order
        context.user_data["current_order_id"] = order["order_id"]

    if payment_type == "reservation":
        amount_due = float(current_order.get("deposit_amount", current_order.get("amount_due", 0) or 0))
        pay_label = "50% deposit"
        note = "This reservation requires the 50% deposit before admin approval."
        payment_summary = (
            f"Order total: {float(current_order.get('total_price', 0)):,.0f} ETB\n"
            f"50% deposit due: {amount_due:,.0f} ETB\n"
            f"Remaining balance: {float(current_order.get('remaining_balance', 0)):,.0f} ETB"
        )
    else:
        amount_due = float(current_order.get("total_price", current_order.get("amount_due", 0) or 0))
        pay_label = "full order total"
        note = "This order requires the full payment before approval."
        payment_summary = (
            f"Order total: {amount_due:,.0f} ETB\n"
            f"Amount due: {amount_due:,.0f} ETB"
        )

    context.user_data["payment_provider"] = provider_name
    context.user_data["payment_type"] = payment_type
    context.user_data["pending_payment_amount"] = amount_due

    if provider_name_upper == "ADMIN":
        message = (
            "📌 PAYMENT INSTRUCTIONS\n\n"
            "Please complete the payment using the approved shop payment method provided by the admin.\n"
            f"{payment_summary} ({pay_label})\n\n"
            f"{note}\n"
            "After payment, submit the payment evidence or transaction number for verification.\n"
            "እባክዎ የሱቃ አስተዳዳሪ የሚያስተላልፍልዎትን የክፍያ አማራጭ ይጠቀሙ እና ከዚያ የክፍያ ማረጋገጫ ያስገቡ።"
        )
    elif provider_name_upper == "CBE":
        message = (
            "🏦 CBE BIRR PAYMENT\n"
            "Account Name: EHD Shop\n"
            "CBE Birr Number: 1000528406479\n"
            f"{payment_summary} ({pay_label})\n\n"
            f"{note}\n"
            "Please transfer the exact amount and then submit your payment evidence.\n"
            "እባክዎ ትክክለኛውን መጠን ያስተላልፉ እና የክፍያዎን ማረጋገጫ ያስገቡ።"
        )
    else:
        message = (
            "📱 TELEBIRR PAYMENT\n"
            "Account Name: EHD Shop\n"
            "Telebirr Number: +251908156093\n"
            f"{payment_summary} ({pay_label})\n\n"
            f"{note}\n"
            "Please transfer the exact amount and then submit your payment evidence.\n"
            "እባክዎ ትክክለኛውን መጠን ያስተላልፉ እና የክፍያዎን ማረጋገጫ ያስገቡ።"
        )

    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(
            update,
            message,
            get_payment_instructions_keyboard(provider_name_upper),
        )
    else:
        await context.bot.send_message(
            chat_id=context.user_data.get("chat_id"),
            text=message,
            reply_markup=get_payment_instructions_keyboard(provider_name_upper),
        )


async def handle_receipt_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, provider: str) -> None:
    context.user_data["payment_provider"] = provider
    context.user_data["awaiting_payment_submission"] = True
    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(
            update,
            "📸 Please upload the payment receipt image or photo to complete verification.\n\n"
            "እባክዎ የክፍያ ስክሪንሾት ይላኩ።",
            InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home / መነሻ", callback_data="home")]]),
        )


async def submit_payment_evidence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return

    current_order = context.user_data.get("current_order") or {}
    order_id = current_order.get("order_id") or context.user_data.get("current_order_id") or "#10001"
    provider = context.user_data.get("payment_provider", "Telebirr")
    amount = context.user_data.get("pending_payment_amount")
    if amount is None:
        if current_order.get("order_type") == "reservation":
            amount = current_order.get("deposit_amount", current_order.get("total_price", 0))
        else:
            amount = current_order.get("total_price", 0)
    amount = float(amount or 0)
    payment_type = context.user_data.get("payment_type") or current_order.get("order_type", "full_payment")
    transaction_number = context.user_data.get("transaction_number")
    screenshot_file_id = None

    if update.message and update.message.photo:
        screenshot_file_id = update.message.photo[-1].file_id

    if not transaction_number and not screenshot_file_id:
        await update.message.reply_text("Please submit a screenshot or transaction number.\n\nእባክዎ የክፍያ ስክሪንሾት ወይም የግብይት ቁጥር ያስገቡ።")
        return

    submission = PaymentService().submit_payment(
        order_id=order_id,
        customer_id=update.effective_user.id,
        payment_method=provider,
        payment_type=payment_type,
        amount=amount,
        transaction_number=transaction_number,
        screenshot_file_id=screenshot_file_id,
        order_data={
            key: current_order.get(key)
            for key in (
                "order_id",
                "telegram_id",
                "order_type",
                "items",
                "total_price",
                "deposit_amount",
                "remaining_balance",
                "amount_due",
            )
        },
        persist=True,
    )

    context.user_data["payment_submission"] = submission
    context.user_data.pop("awaiting_payment_submission", None)
    context.user_data.pop("transaction_number", None)
    await update.message.reply_text(
        "✅ Payment evidence submitted successfully.\n"
        "Your payment is pending admin verification.\n\n"
        "የክፍያ ማረጋገጫዎ በተሳካ ሁኔታ ተላልፏል። ክፍያዎ አሁን በአስተዳዳሪ ማረጋገጥ ላይ ነው።"
    )

    admin_message = (
        "💳 New payment submission\n"
        f"Order: {order_id}\n"
        f"Customer ID: {update.effective_user.id}\n"
        f"Method: {provider}\n"
        f"Amount: {amount:,.0f} ETB\n"
        f"Type: {payment_type}"
    )
    if transaction_number:
        admin_message += f"\nTransaction: {transaction_number}"

    for admin_id in ADMIN_IDS:
        try:
            if screenshot_file_id:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=screenshot_file_id,
                    caption=admin_message,
                    reply_markup=get_admin_review_keyboard(order_id),
                )
            else:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message,
                    reply_markup=get_admin_review_keyboard(order_id),
                )
        except TelegramError:
            logger.exception("Unable to notify admin %s about payment for %s", admin_id, order_id)


async def handle_transaction_number(update: Update, context: ContextTypes.DEFAULT_TYPE, provider: str) -> None:
    context.user_data["payment_provider"] = provider
    context.user_data["awaiting_payment_submission"] = True
    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(
            update,
            "🔢 Please send the transaction number now.\n\nየግብይት ቁጥሩን አሁን ይላኩ።"
        )


def handle_payment() -> str:
    return "Payment placeholder."
