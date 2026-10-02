import re
import logging
from typing import Any, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

try:
    from ehd_shope.config import ADMIN_IDS
    from ehd_shope.handlers.message_utils import edit_callback_message
    from ehd_shope.services.inventory_service import InventoryService
    from ehd_shope.services.order_service import OrderService
    from ehd_shope.services.payment_service import PaymentService
except ImportError:
    from config import ADMIN_IDS
    from handlers.message_utils import edit_callback_message
    from services.inventory_service import InventoryService
    from services.order_service import OrderService
    from services.payment_service import PaymentService

logger = logging.getLogger(__name__)


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("📦 Products", callback_data="admin_products")],
        [InlineKeyboardButton("📋 Orders", callback_data="admin_orders")],
        [InlineKeyboardButton("💳 Payments", callback_data="admin_payments")],
        [InlineKeyboardButton("👥 Customers", callback_data="admin_customers")],
        [InlineKeyboardButton("📈 Sales", callback_data="admin_sales")],
    ])


def get_product_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Product", callback_data="admin_add_product")],
        [InlineKeyboardButton("✏️ Edit Product", callback_data="admin_list_edit_products")],
        [InlineKeyboardButton("🗑️ Delete Product", callback_data="admin_list_delete_products")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")],
    ])


def get_admin_product_management_keyboard(action: str) -> InlineKeyboardMarkup:
    products = InventoryService().list_products()
    rows: list[list[InlineKeyboardButton]] = []
    for product in products:
        label = product.get("name", "Product")
        callback = f"admin_{action}:{product.get('id')}"
        rows.append([InlineKeyboardButton(f"{label}", callback_data=callback)])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def get_category_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Electronics", callback_data="admin_category:electronics")],
        [InlineKeyboardButton("👟 Shoes", callback_data="admin_category:shoes")],
        [InlineKeyboardButton("👕 Clothes", callback_data="admin_category:clothes")],
        [InlineKeyboardButton("💊 Drugstore", callback_data="admin_category:drugstore")],
    ])


def get_admin_review_keyboard(order_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve:{order_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject:{order_id}")],
    ])


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("Unable to identify you.")
        return

    if user.id not in ADMIN_IDS:
        await update.message.reply_text("You do not have admin access.")
        return

    await update.message.reply_text("👨‍💼 ADMIN PANEL", reply_markup=get_admin_main_keyboard())


async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()

    pending = PaymentService().list_pending()
    reserved = OrderService().get_reserved_orders()
    reserved_summary = OrderService().get_reserved_product_summary()

    lines = ["📊 ADMIN DASHBOARD", ""]
    lines.append(f"Pending payments: {len(pending)}")
    if pending:
        for payment in pending:
            lines.append(
                f"- Customer: {payment.get('customer_id')} | "
                f"Order: {payment.get('order_id')} | "
                f"Amount: {float(payment.get('amount', 0)):,.0f} ETB | "
                f"Method: {payment.get('payment_method', 'Unknown')}"
            )
    else:
        lines.append("- No customer payment submissions pending.")

    lines.append("")
    lines.append(f"Reserved products: {len(reserved_summary)}")
    if reserved_summary:
        for item in reserved_summary:
            lines.append(
                f"- Order: {item['order_id']} | Customer: {item['customer_id']} | "
                f"Products: {item['products']} | Amount: {float(item['amount_due'] or 0):,.0f} ETB"
            )
    else:
        lines.append("- No reserved products yet.")

    text = "\n".join(lines)
    if update.callback_query:
        await edit_callback_message(update, text, get_admin_main_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_admin_main_keyboard())


async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(update, "📦 Products", get_product_actions_keyboard())


async def admin_list_edit_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(
            update,
            "✏️ Select a product to edit.",
            get_admin_product_management_keyboard("edit_product"),
        )


async def admin_list_delete_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        await edit_callback_message(
            update,
            "🗑️ Select a product to delete.",
            get_admin_product_management_keyboard("delete_product"),
        )


async def admin_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str) -> None:
    query = update.callback_query
    if not query:
        return
    product = InventoryService().get_product(product_id)
    if not product:
        await query.answer("Product not found.", show_alert=True)
        return
    context.user_data["editing_product_id"] = product_id
    await query.answer()
    await edit_callback_message(
        update,
        "✏️ Edit product\n\n"
        f"Current: {product.get('name', 'Unknown')}\n"
        f"Price: {float(product.get('price', 0)):,.0f} ETB\n"
        f"Stock: {product.get('stock_quantity', 0)}\n\n"
        "Send updated values in this format:\n"
        "Name|Description|Price|Stock|Status",
    )


async def admin_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str) -> None:
    query = update.callback_query
    if not query:
        return

    try:
        deleted = InventoryService().delete_product(product_id)
        await query.answer("✅ Product deleted." if deleted else "Product not found.", show_alert=not deleted)
        await edit_callback_message(update, "🗑️ Product removed from catalog.", get_product_actions_keyboard())
    except Exception:
        await query.answer("Unable to delete product.", show_alert=True)


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()

    text = "📋 ORDER LIST\n\nNo order list is stored in the local database yet.\nUse the payment approval queue to review customer orders."
    if update.callback_query:
        await edit_callback_message(update, text, get_admin_main_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_admin_main_keyboard())


async def admin_customers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()

    text = "👥 CUSTOMERS\n\nCustomer records are tracked through Telegram IDs and order history.\nNo manual customer list is required for the current workflow."
    if update.callback_query:
        await edit_callback_message(update, text, get_admin_main_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_admin_main_keyboard())


async def admin_sales(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()

    text = "📈 SALES OVERVIEW\n\nThis dashboard shows the total verified sales and pending approvals from payment submissions."
    if update.callback_query:
        await edit_callback_message(update, text, get_admin_main_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=get_admin_main_keyboard())


async def admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()

    pending = PaymentService().list_pending()
    if not pending:
        text = "💳 No pending payment submissions."
        keyboard = get_admin_main_keyboard()
    else:
        lines = ["💳 PENDING PAYMENTS\n"]
        rows: list[list[InlineKeyboardButton]] = []
        for item in pending:
            lines.append(
                f"Order ID: {item['order_id']}\n"
                f"Customer: {item['customer_id']}\n"
                f"Method: {item['payment_method']}\n"
                f"Amount: {float(item['amount']):,.0f} ETB\n"
                f"Status: {item['status']}\n"
            )
            rows.extend(get_admin_review_keyboard(item["order_id"]).inline_keyboard)
        rows.append([InlineKeyboardButton("🏠 Admin menu", callback_data="admin_dashboard")])
        keyboard = InlineKeyboardMarkup(rows)
        text = "\n".join(lines)
    if update.callback_query:
        await edit_callback_message(update, text, keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)


async def admin_add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await edit_callback_message(
        update,
        "Choose product category:",
        get_category_keyboard(),
    )


async def admin_set_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    context.user_data["new_product_category"] = category
    await update.callback_query.answer()
    await edit_callback_message(
        update,
        f"📂 Category selected: {category.title()}\n\nPlease send the product image.",
    )
    context.user_data["product_creation_step"] = "image"


async def admin_store_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    image_file_id = None
    image_source_type = None
    if update.message.photo:
        image_file_id = update.message.photo[-1].file_id
        image_source_type = "photo"
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("image/"):
        image_file_id = update.message.document.file_id
        image_source_type = "document"

    if not image_file_id:
        await update.message.reply_text("Please send a valid product image.")
        return

    context.user_data["new_product_image"] = image_file_id
    context.user_data["new_product_image_type"] = image_source_type
    context.user_data["product_creation_step"] = "name"
    await update.message.reply_text("🏷️ Enter product name:")


async def admin_store_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    context.user_data["new_product_name"] = update.message.text
    context.user_data["product_creation_step"] = "description"
    await update.message.reply_text("📝 Enter product description:")


async def admin_store_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    context.user_data["new_product_description"] = update.message.text
    context.user_data["product_creation_step"] = "price"
    await update.message.reply_text("💰 Enter product price in ETB (example: 250 or 250 ETB):")


def parse_price_value(raw_text: str) -> float:
    cleaned = (raw_text or "").strip()
    if not cleaned:
        raise ValueError("Price is empty.")

    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    if not match:
        raise ValueError("No numeric price found.")

    value = float(match.group(0))
    if value <= 0:
        raise ValueError("Price must be greater than zero.")

    return value


async def admin_store_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    try:
        price = parse_price_value(update.message.text)
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid price in ETB, such as 250 or 250 ETB.")
        return

    context.user_data["new_product_price"] = price
    context.user_data["product_creation_step"] = "stock"
    await update.message.reply_text("📦 Enter product stock:")


async def admin_store_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    context.user_data["new_product_stock"] = int(update.message.text)
    context.user_data["product_creation_step"] = "details"
    await update.message.reply_text(
        "Describe the product details for the customer.\n"
        "Add only the product information the customer should know, such as material or style.\n"
        "Do not ask customers to choose a size or color."
    )


async def admin_store_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    details = update.message.text
    context.user_data["new_product_details"] = details
    product = {
        "category": context.user_data["new_product_category"],
        "image_file_id": context.user_data.get("new_product_image"),
        "image_url": context.user_data.get("new_product_image"),
        "image_source_type": context.user_data.get("new_product_image_type", "photo"),
        "name": context.user_data["new_product_name"],
        "name_am": context.user_data.get("new_product_name", ""),
        "description": context.user_data["new_product_description"],
        "description_am": context.user_data.get("new_product_description", ""),
        "details": details,
        "price": context.user_data["new_product_price"],
        "stock_quantity": context.user_data["new_product_stock"],
        "stock": context.user_data["new_product_stock"],
        "is_active": True,
        "status": "available",
        "sizes": [],
        "colors": [],
    }
    InventoryService().add_product(product, persist=True)
    await update.message.reply_text(
        "✅ Product saved to database.\n"
        "Customer can see it immediately in the selected category."
    )
    context.user_data.pop("new_product_category", None)
    context.user_data.pop("new_product_image", None)
    context.user_data.pop("new_product_image_type", None)
    context.user_data.pop("new_product_name", None)
    context.user_data.pop("new_product_description", None)
    context.user_data.pop("new_product_price", None)
    context.user_data.pop("new_product_stock", None)
    context.user_data.pop("new_product_details", None)
    context.user_data.pop("product_creation_step", None)


async def admin_review(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        await edit_callback_message(
            update,
            f"Review payment for order {order_id}",
            get_admin_review_keyboard(order_id),
        )


async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> None:
    query = update.callback_query
    if query:
        try:
            reviewed = PaymentService().approve_payment(order_id)
            await query.answer("✅ Payment approved.")
            await edit_callback_message(
                update,
                f"✅ Approved payment for order {order_id}.\n"
                f"Status: {reviewed['status']}\n"
                f"Amount: {float(reviewed['amount']):,.0f} ETB",
                get_admin_main_keyboard(),
            )
            payment_type = str(reviewed.get("payment_type", "full_payment")).lower()
            order_status = "reserved" if payment_type == "reservation" else "paid"
            customer_message = (
                f"✅ Your payment for order {order_id} has been approved.\n"
                f"Payment status: accepted. Order status: {order_status}.\n\n"
                "ክፍያዎ ጸድቋል። ትዕዛዝዎ ተቀባይነት አግኝቷል።"
            )
            try:
                await context.bot.send_message(
                    chat_id=reviewed["customer_id"],
                    text=customer_message,
                )
            except TelegramError:
                logger.exception("Unable to notify customer about approved payment %s", order_id)
        except ValueError as error:
            if str(error).startswith("No payment submission found"):
                await query.answer("This payment review link is outdated.", show_alert=True)
                await edit_callback_message(
                    update,
                    "⚠️ This payment was submitted before review records were saved across restarts. "
                    "Its order items cannot be recovered, so no stock was reserved.\n\n"
                    "Ask the customer to rebuild the same order and resubmit the existing receipt or "
                    "transaction number. They should not transfer the money again.",
                    get_admin_main_keyboard(),
                )
            else:
                await query.answer(str(error), show_alert=True)


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str) -> None:
    query = update.callback_query
    if query:
        try:
            rejected = PaymentService().reject_payment(order_id)
            await query.answer("❌ Payment rejected.")
            await edit_callback_message(
                update,
                f"❌ Rejected payment for order {order_id}.\n"
                f"Reason: {rejected.get('reason', 'Unspecified')}",
                get_admin_main_keyboard(),
            )
            try:
                await context.bot.send_message(
                    chat_id=rejected["customer_id"],
                    text=(
                        f"❌ Your payment for order {order_id} was not approved.\n"
                        f"Reason: {rejected.get('reason', 'Unspecified')}\n"
                        "Please contact the shop or submit new payment evidence."
                    ),
                )
            except TelegramError:
                logger.exception("Unable to notify customer about rejected payment %s", order_id)
        except ValueError:
            await query.answer("This payment review link is outdated.", show_alert=True)
            await edit_callback_message(
                update,
                "⚠️ This payment review link is outdated. The payment record is unavailable.\n\n"
                "Ask the customer to rebuild the same order and resubmit the existing receipt or "
                "transaction number. They should not transfer the money again.",
                get_admin_main_keyboard(),
            )


async def handle_admin_product_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not context.user_data.get("editing_product_id"):
        return

    product_id = context.user_data["editing_product_id"]
    raw = update.message.text.strip()
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 5:
        await update.message.reply_text("Invalid format. Use: Name|Description|Price|Stock|Status")
        return

    try:
        updated = InventoryService().update_product(
            product_id,
            {
                "name": parts[0],
                "description": parts[1],
                "price": float(parts[2]),
                "stock_quantity": int(parts[3]),
                "status": parts[4],
            },
        )
        context.user_data.pop("editing_product_id", None)
        await update.message.reply_text(
            "✅ Product updated successfully.\n"
            f"Name: {updated.get('name')}\n"
            f"Price: {float(updated.get('price', 0)):,.0f} ETB\n"
            f"Stock: {updated.get('stock_quantity', 0)}\n"
            f"Status: {updated.get('status', 'available')}"
        )
    except ValueError:
        await update.message.reply_text("Product was not found.")
    except (TypeError, ValueError):
        await update.message.reply_text("Invalid values. Use numeric price and stock.")


async def admin_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or user.id not in ADMIN_IDS:
        if update.message:
            await update.message.reply_text("You do not have admin access.")
        elif update.callback_query:
            await update.callback_query.answer("No access", show_alert=True)
        return

    products = InventoryService().list_products()
    if not products:
        await update.message.reply_text("No products in database.")
        return

    lines = []
    for p in products:
        pid = str(p.get("_id"))
        name = p.get("name", "<no name>")
        price = p.get("price", 0)
        stock = p.get("stock", 0)
        has_image = "yes" if p.get("image_file_id") or p.get("image_url") else "no"
        lines.append(f"{pid} — {name} — {int(price)} ETB — stock {stock} — image:{has_image}")

    # send in chunks if long
    chunk_size = 10
    for i in range(0, len(lines), chunk_size):
        await update.message.reply_text("\n".join(lines[i : i + chunk_size]))
