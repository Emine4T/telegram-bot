from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

try:
    from ehd_shope.config import TELEGRAM_BOT_TOKEN
    from ehd_shope.database.database import init_db
    from ehd_shope.handlers.admin import (
        admin_add_product_start,
        admin_approve,
        admin_command,
        admin_dashboard,
        admin_delete_product,
        admin_edit_product,
        admin_list_delete_products,
        admin_list_edit_products,
        admin_orders,
        admin_payments,
        admin_products,
        admin_reject,
        admin_review,
        admin_sales,
        admin_set_category,
        admin_customers,
        admin_store_description,
        admin_store_details,
        admin_store_image,
        admin_store_name,
        admin_store_price,
        admin_store_stock,
        admin_list_products,
        handle_admin_product_edit_text,
    )
    from ehd_shope.handlers.auth import auth_command
    from ehd_shope.handlers.cart import cart_command, handle_cart_action, show_cart
    from ehd_shope.handlers.checkout import checkout_command, start_payment_selection
    from ehd_shope.handlers.payment import (
        handle_receipt_upload,
        handle_transaction_number,
        payment_command,
        show_payment_instructions,
        submit_payment_evidence,
    )
    from ehd_shope.handlers.shop import handle_add_to_cart, shop_command, show_category, show_product_card
    from ehd_shope.handlers.start import home_command, my_orders_command, start_command, toggle_language
    from ehd_shope.handlers.support import end_support_command, handle_support_message, support_command
except ImportError:
    from config import TELEGRAM_BOT_TOKEN
    from database.database import init_db
    from handlers.admin import (
        admin_add_product_start,
        admin_approve,
        admin_command,
        admin_dashboard,
        admin_delete_product,
        admin_edit_product,
        admin_list_delete_products,
        admin_list_edit_products,
        admin_orders,
        admin_payments,
        admin_products,
        admin_reject,
        admin_review,
        admin_sales,
        admin_set_category,
        admin_customers,
        admin_store_description,
        admin_store_details,
        admin_store_image,
        admin_store_name,
        admin_store_price,
        admin_store_stock,
        admin_list_products,
        handle_admin_product_edit_text,
    )
    from handlers.auth import auth_command
    from handlers.cart import cart_command, handle_cart_action, show_cart
    from handlers.checkout import checkout_command, start_payment_selection
    from handlers.payment import (
        handle_receipt_upload,
        handle_transaction_number,
        payment_command,
        show_payment_instructions,
        submit_payment_evidence,
    )
    from handlers.shop import handle_add_to_cart, shop_command, show_category, show_product_card
    from handlers.start import home_command, my_orders_command, start_command, toggle_language
    from handlers.support import end_support_command, handle_support_message, support_command

load_dotenv()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    data = query.data

    if data == "home":
        await home_command(update, context)
    elif data == "my_orders":
        await my_orders_command(update, context)
    elif data == "language":
        await toggle_language(update, context)
    elif data == "admin_dashboard":
        await admin_dashboard(update, context)
    elif data == "admin_products":
        await admin_products(update, context)
    elif data == "admin_orders":
        await admin_orders(update, context)
    elif data == "admin_customers":
        await admin_customers(update, context)
    elif data == "admin_sales":
        await admin_sales(update, context)
    elif data == "admin_payments":
        await admin_payments(update, context)
    elif data == "admin_add_product":
        await admin_add_product_start(update, context)
    elif data == "admin_list_edit_products":
        await admin_list_edit_products(update, context)
    elif data == "admin_list_delete_products":
        await admin_list_delete_products(update, context)
    elif data.startswith("admin_category:"):
        await admin_set_category(update, context, data.split(":", 1)[1])
    elif data.startswith("product:"):
        await show_product_card(update, context, data.split(":", 1)[1])
    elif data.startswith("category:"):
        await show_category(update, context, data.split(":", 1)[1])
    elif data.startswith("add_to_cart:"):
        await handle_add_to_cart(update, context, data.split(":", 1)[1])
    elif data.startswith("cart:"):
        await handle_cart_action(update, context, data.split(":", 1)[1])
    elif data == "show_cart":
        await show_cart(update, context)
    elif data == "checkout":
        await start_payment_selection(update, context)
    elif data.startswith("payment:"):
        await show_payment_instructions(update, context, data.split(":", 1)[1])
    elif data.startswith("upload_receipt:"):
        await handle_receipt_upload(update, context, data.split(":", 1)[1])
    elif data.startswith("enter_txn:"):
        await handle_transaction_number(update, context, data.split(":", 1)[1])
    elif data.startswith("admin_review:"):
        await admin_review(update, context, data.split(":", 1)[1])
    elif data.startswith("admin_approve:"):
        await admin_approve(update, context, data.split(":", 1)[1])
    elif data.startswith("admin_reject:"):
        await admin_reject(update, context, data.split(":", 1)[1])
    elif data.startswith("admin_edit_product:"):
        await admin_edit_product(update, context, data.split(":", 1)[1])
    elif data.startswith("admin_delete_product:"):
        await admin_delete_product(update, context, data.split(":", 1)[1])
    else:
        await query.answer("Unknown action", show_alert=True)


async def handle_product_form_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if context.user_data.get("awaiting_payment_submission"):
        context.user_data["transaction_number"] = update.message.text.strip()
        await submit_payment_evidence(update, context)
        return

    if context.user_data.get("editing_product_id"):
        await handle_admin_product_edit_text(update, context)
        return

    step = context.user_data.get("product_creation_step")
    if step == "image":
        await admin_store_image(update, context)
    elif step == "name":
        await admin_store_name(update, context)
    elif step == "description":
        await admin_store_description(update, context)
    elif step == "price":
        await admin_store_price(update, context)
    elif step == "stock":
        await admin_store_stock(update, context)
    elif step == "details":
        await admin_store_details(update, context)
    elif context.user_data.get("support_chat_active"):
        await handle_support_message(update, context)


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("awaiting_payment_submission"):
        await submit_payment_evidence(update, context)
        return

    if context.user_data.get("product_creation_step") == "image":
        await admin_store_image(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/start - welcome message\n"
        "/auth - register account\n"
        "/shop - view products\n"
        "/cart - view cart\n"
        "/checkout - start checkout\n"
        "/payment - payment instructions\n"
        "/support - AI support chat\n"
        "/endsupport - end AI support chat\n"
        "/admin - admin panel"
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    init_db()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("auth", auth_command))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("cart", cart_command))
    application.add_handler(CommandHandler("checkout", checkout_command))
    application.add_handler(CommandHandler("payment", payment_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CommandHandler("endsupport", end_support_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("list_products", admin_list_products))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_form_text))

    application.run_polling()


if __name__ == "__main__":
    main()
