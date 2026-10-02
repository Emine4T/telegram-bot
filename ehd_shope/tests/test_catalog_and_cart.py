import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from copy import deepcopy

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.error import BadRequest

from ehd_shope.handlers.admin import admin_approve, admin_dashboard, admin_payments
from ehd_shope.handlers.cart import get_cart_keyboard, show_cart
from ehd_shope.handlers.payment import handle_transaction_number, submit_payment_evidence
from ehd_shope.handlers.message_utils import edit_callback_message
from ehd_shope.handlers.shop import can_edit_message_caption, handle_add_to_cart, show_product_card
from ehd_shope.handlers.start import toggle_language
from ehd_shope.services.inventory_service import InventoryService
from ehd_shope.services.order_service import OrderService
from ehd_shope.services.payment_service import PaymentService
import ehd_shope.services.inventory_service as inventory_module


class CatalogAndCartTests(unittest.TestCase):
    def test_product_catalog_has_categories_and_products(self):
        service = InventoryService()
        products = service.list_products_by_category("electronics")
        self.assertGreater(len(products), 0)
        self.assertIn("Smartphone", [p["name"] for p in products])

    def test_order_summary_calculates_total_and_items(self):
        cart = [
            {"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1},
            {"product_id": "sneaker-1", "name": "Sneakers", "price": 3000, "quantity": 2},
        ]
        summary = OrderService().build_order_summary(cart)
        self.assertEqual(summary["total"], 31000)
        self.assertEqual(len(summary["items"]), 2)

    def test_cart_sync_updates_payment_total_for_checkout(self):
        cart = [{"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1}]
        state = OrderService().build_cart_payment_state(telegram_id=123, cart=cart, order_type="full_payment")
        self.assertEqual(state["total_price"], 25000)
        self.assertEqual(state["amount_due"], 25000)

    def test_cart_keyboard_includes_payment_options(self):
        keyboard = get_cart_keyboard([
            {"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1, "item_key": "smartphone-1|default|default"}
        ])
        labels = [button.text for row in keyboard.inline_keyboard for button in row]
        self.assertIn("💳 Telebirr", labels)
        self.assertIn("🏦 CBE Birr", labels)
        self.assertTrue(any("Reserve 50%" in label for label in labels))

    def test_callback_edits_photo_caption_instead_of_text(self):
        query = SimpleNamespace(
            message=SimpleNamespace(photo=[object()], reply_text=AsyncMock()),
            edit_message_caption=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query)

        async def run_test() -> None:
            await edit_callback_message(update, "Cart", get_cart_keyboard([]))

        asyncio.run(run_test())
        query.edit_message_caption.assert_awaited_once()
        query.edit_message_text.assert_not_awaited()

    def test_add_to_cart_answers_callback_once(self):
        product = {"id": "smartphone-1", "category": "electronics", "name": "Smartphone", "price": 25000}
        query = SimpleNamespace(answer=AsyncMock())
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=123))
        context = SimpleNamespace(user_data={})

        async def run_test() -> None:
            with patch.object(InventoryService, "get_product", return_value=product), patch(
                "ehd_shope.handlers.shop.edit_navigation_message", new_callable=AsyncMock
            ) as navigation_mock:
                await handle_add_to_cart(update, context, "smartphone-1")
                navigation_mock.assert_awaited_once()
                self.assertEqual(context.user_data["selected_category"], "electronics")
                self.assertEqual(context.user_data["cart"][0]["product_id"], "smartphone-1")

        asyncio.run(run_test())
        query.answer.assert_awaited_once_with("✅ Product added to your cart.")

    def test_language_toggle_answers_callback_once(self):
        query = SimpleNamespace(answer=AsyncMock())
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(user_data={"language": "en"})

        async def run_test() -> None:
            with patch("ehd_shope.handlers.start.edit_home_message", new_callable=AsyncMock):
                await toggle_language(update, context)

        asyncio.run(run_test())
        query.answer.assert_awaited_once_with("Language set to am.")
        self.assertEqual(context.user_data["language"], "am")

    def test_payment_button_creates_order_and_keeps_provider(self):
        from ehd_shope.handlers.payment import show_payment_instructions

        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(photo=[object()], reply_text=AsyncMock()),
            edit_message_caption=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=123))
        context = SimpleNamespace(
            user_data={
                "cart": [{"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1}]
            }
        )

        async def run_test() -> None:
            await show_payment_instructions(update, context, "CBE|full_payment")

        asyncio.run(run_test())
        self.assertTrue(context.user_data["current_order_id"].startswith("#ORD-"))
        self.assertEqual(context.user_data["payment_provider"], "CBE")
        query.edit_message_caption.assert_awaited_once()

    def test_reservation_selection_creates_order_for_half_deposit(self):
        from ehd_shope.handlers.payment import show_payment_instructions

        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(photo=[object()], reply_text=AsyncMock()),
            edit_message_caption=AsyncMock(),
            edit_message_text=AsyncMock(),
        )
        cart = [{"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1}]
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=123))
        context = SimpleNamespace(
            user_data={
                "cart": cart,
                "current_order": OrderService().build_cart_payment_state(123, cart, "full_payment"),
            }
        )

        async def run_test() -> None:
            await show_payment_instructions(update, context, "Telebirr|reservation")

        asyncio.run(run_test())
        self.assertEqual(context.user_data["current_order"]["order_type"], "reservation")
        self.assertEqual(context.user_data["pending_payment_amount"], 12500)
        self.assertEqual(context.user_data["current_order"]["remaining_balance"], 12500)

    def test_payment_instructions_show_combined_multi_product_totals(self):
        from ehd_shope.handlers.payment import show_payment_instructions

        cart = [
            {"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1},
            {"product_id": "headphones-1", "name": "Headphones", "price": 4500, "quantity": 2},
        ]
        order_service = OrderService()
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(photo=None, reply_text=AsyncMock()),
        )
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=123))

        async def show_and_capture(payment_choice):
            context = SimpleNamespace(user_data={"cart": cart})
            with patch("ehd_shope.handlers.payment.edit_callback_message", new_callable=AsyncMock) as edit:
                await show_payment_instructions(update, context, payment_choice)
            return edit.await_args.args[1]

        async def run_test() -> None:
            full_payment_text = await show_and_capture("CBE|full_payment")
            reservation_text = await show_and_capture("CBE|reservation")

            self.assertEqual(order_service.build_order_summary(cart)["total"], 34000)
            self.assertIn("Order total: 34,000 ETB", full_payment_text)
            self.assertIn("Amount due: 34,000 ETB", full_payment_text)
            self.assertIn("Order total: 34,000 ETB", reservation_text)
            self.assertIn("50% deposit due: 17,000 ETB", reservation_text)
            self.assertIn("Remaining balance: 17,000 ETB", reservation_text)

        asyncio.run(run_test())

    def test_stock_validation_prevents_over_ordering(self):
        service = InventoryService()
        self.assertTrue(service.validate_stock("smartphone-1", 8))
        self.assertFalse(service.validate_stock("smartphone-1", 9))

    def test_order_reservation_uses_half_deposit_and_half_remaining_balance(self):
        order = OrderService().create_order(
            telegram_id=123,
            cart=[{"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1}],
            order_type="reservation",
        )
        self.assertEqual(order["deposit_amount"], 12500)
        self.assertEqual(order["remaining_balance"], 12500)
        self.assertEqual(order["order_status"], "awaiting_payment")

    def test_payment_approval_updates_order_status(self):
        service = PaymentService()
        inventory = InventoryService()
        stock_before = inventory.get_stock("smartphone-1")
        order = OrderService().create_order(
            telegram_id=123,
            cart=[{"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1}],
            order_type="reservation",
        )
        submission = service.submit_payment(
            order_id=order["order_id"],
            customer_id=123,
            payment_method="Telebirr",
            payment_type="reservation",
            amount=12500,
            transaction_number="TX456",
        )
        self.assertEqual(submission["status"], "pending")
        approved = service.approve_payment(order["order_id"])
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["order_status"], "reserved")
        self.assertEqual(inventory.get_stock("smartphone-1"), stock_before - 1)
        for product in inventory_module.PRODUCT_CATALOG:
            if product["id"] == "smartphone-1":
                product["stock_quantity"] = stock_before
                break

    def test_persisted_reservation_can_be_approved_after_service_restart(self):
        from ehd_shope.database.database import Base

        engine = create_engine("sqlite://")
        session_factory = sessionmaker(bind=engine)
        existing_submissions = PaymentService._submissions.copy()
        order_data = {
            "order_id": "#ORD-PERSIST-TEST",
            "order_type": "reservation",
            "items": [{"product_id": "smartphone-1", "quantity": 2}],
        }
        try:
            Base.metadata.create_all(bind=engine)
            with patch("ehd_shope.database.database.SessionLocal", session_factory):
                PaymentService._submissions.clear()
                PaymentService().submit_payment(
                    order_id=order_data["order_id"],
                    customer_id=123,
                    payment_method="Telebirr",
                    payment_type="reservation",
                    amount=25000,
                    order_data=order_data,
                    persist=True,
                )

                PaymentService._submissions.clear()
                restarted_service = PaymentService()
                self.assertEqual(restarted_service.get_submission(order_data["order_id"])["status"], "pending")

                with patch.object(InventoryService, "reserve_items", return_value=True) as reserve_items:
                    approved = restarted_service.approve_payment(order_data["order_id"])

                self.assertEqual(approved["status"], "approved")
                reserve_items.assert_called_once_with(order_data["items"])
                self.assertEqual(
                    restarted_service.get_submission(order_data["order_id"])["status"],
                    "approved",
                )
        finally:
            PaymentService._submissions[:] = existing_submissions
            engine.dispose()

    def test_admin_approval_notifies_customer(self):
        submission = {
            "order_id": "#ORD-APPROVE-1",
            "customer_id": 456,
            "payment_type": "full_payment",
            "amount": 1250,
            "status": "approved",
        }
        query = SimpleNamespace(answer=AsyncMock(), message=SimpleNamespace(photo=None, reply_text=AsyncMock()))
        update = SimpleNamespace(callback_query=query)
        bot = SimpleNamespace(send_message=AsyncMock())
        context = SimpleNamespace(bot=bot)

        async def run_test() -> None:
            with patch.object(PaymentService, "approve_payment", return_value=submission), patch(
                "ehd_shope.handlers.admin.edit_callback_message", new_callable=AsyncMock
            ):
                await admin_approve(update, context, submission["order_id"])

        asyncio.run(run_test())
        bot.send_message.assert_awaited_once()
        self.assertEqual(bot.send_message.await_args.kwargs["chat_id"], 456)
        self.assertIn("has been approved", bot.send_message.await_args.kwargs["text"])

    def test_admin_approval_explains_missing_legacy_payment(self):
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(photo=None, reply_text=AsyncMock()),
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(bot=SimpleNamespace())
        edit_mock = AsyncMock()

        async def run_test() -> None:
            with patch.object(
                PaymentService,
                "approve_payment",
                side_effect=ValueError("No payment submission found for order #ORD-00002"),
            ), patch("ehd_shope.handlers.admin.edit_callback_message", edit_mock):
                await admin_approve(update, context, "#ORD-00002")

        asyncio.run(run_test())
        query.answer.assert_awaited_once_with("This payment review link is outdated.", show_alert=True)
        self.assertIn("should not transfer the money again", edit_mock.await_args.args[1])

    def test_admin_payments_lists_approval_buttons(self):
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(photo=None, reply_text=AsyncMock()),
            edit_message_text=AsyncMock(),
            edit_message_caption=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace()
        pending = [{
            "order_id": "#ORD-PENDING-1",
            "customer_id": 456,
            "payment_method": "Telebirr",
            "amount": 1250,
            "status": "pending",
        }]

        async def run_test() -> None:
            with patch.object(PaymentService, "list_pending", return_value=pending):
                await admin_payments(update, context)

        asyncio.run(run_test())
        buttons = [
            button
            for row in query.edit_message_text.await_args.kwargs["reply_markup"].inline_keyboard
            for button in row
        ]
        self.assertIn("admin_approve:#ORD-PENDING-1", [button.callback_data for button in buttons])

    def test_payment_submission_sends_admin_approval_buttons(self):
        message = SimpleNamespace(text="TX-123", photo=None, reply_text=AsyncMock())
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=456),
        )
        bot = SimpleNamespace(send_message=AsyncMock())
        context = SimpleNamespace(
            bot=bot,
            user_data={
                "current_order": {"order_id": "#ORD-SUBMIT-1", "total_price": 2500},
                "payment_provider": "Telebirr",
                "payment_type": "full_payment",
                "transaction_number": "TX-123",
            },
        )
        submission = {
            "order_id": "#ORD-SUBMIT-1",
            "customer_id": 456,
            "payment_method": "Telebirr",
            "payment_type": "full_payment",
            "amount": 2500,
            "status": "pending",
        }

        async def run_test() -> None:
            with patch("ehd_shope.handlers.payment.ADMIN_IDS", [321]), patch.object(
                PaymentService,
                "submit_payment",
                return_value=submission,
            ):
                await submit_payment_evidence(update, context)

        asyncio.run(run_test())
        bot.send_message.assert_awaited_once()
        notification = bot.send_message.await_args.kwargs
        self.assertEqual(notification["chat_id"], 321)
        self.assertIn("TX-123", notification["text"])
        buttons = [button for row in notification["reply_markup"].inline_keyboard for button in row]
        self.assertIn("admin_approve:#ORD-SUBMIT-1", [button.callback_data for button in buttons])

    def test_product_update_and_delete_work_for_admin_management(self):
        service = InventoryService()
        created = service.add_product({
            "category": "electronics",
            "name": "Tablet Test",
            "price": 5000,
            "stock_quantity": 3,
            "status": "available",
            "sizes": [],
            "colors": [],
        })
        updated = service.update_product(created["id"], {"price": 7000, "stock_quantity": 9, "status": "hidden"})
        self.assertEqual(updated["price"], 7000)
        self.assertEqual(updated["stock_quantity"], 9)
        self.assertEqual(updated["status"], "hidden")
        self.assertTrue(service.delete_product(created["id"]))

    def test_admin_products_persist_with_document_image_metadata(self):
        from ehd_shope.database.database import Base

        engine = create_engine("sqlite://")
        original_catalog = deepcopy(inventory_module.PRODUCT_CATALOG)
        session_factory = sessionmaker(bind=engine)
        try:
            with patch("ehd_shope.database.database.SessionLocal", session_factory), patch.object(
                inventory_module,
                "PRODUCT_CATALOG",
                deepcopy(original_catalog),
            ) as catalog:
                Base.metadata.create_all(bind=engine)
                service = InventoryService()
                created = service.add_product(
                    {
                        "category": "drugstore",
                        "name": "Persistent product",
                        "description": "Saved across restarts",
                        "price": 250,
                        "stock_quantity": 4,
                        "image_file_id": "document-file-id",
                        "image_source_type": "document",
                    },
                    persist=True,
                )

                catalog[:] = deepcopy(original_catalog)
                restored = service.get_product(created["id"])
                self.assertEqual(restored["image_file_id"], "document-file-id")
                self.assertEqual(restored["image_source_type"], "document")
                self.assertTrue(service.reserve_items([{"product_id": created["id"], "quantity": 2}]))
                catalog[:] = deepcopy(original_catalog)
                self.assertEqual(service.get_product(created["id"])["stock_quantity"], 2)
                self.assertTrue(
                    any(item["id"] == created["id"] for item in service.list_products_by_category("drugstore"))
                )
                self.assertTrue(service.delete_product(created["id"]))
        finally:
            engine.dispose()

    def test_photo_messages_use_caption_editing_for_back_navigation(self):
        self.assertTrue(can_edit_message_caption(SimpleNamespace(photo=[object()])))
        self.assertFalse(can_edit_message_caption(SimpleNamespace(photo=None)))

    def test_payment_submission_and_approval_flow(self):
        service = PaymentService()
        submission = service.submit_payment(
            order_id="#10001",
            customer_id=123,
            payment_method="Telebirr",
            payment_type="full_payment",
            amount=25000,
            transaction_number="TX123",
        )
        self.assertEqual(submission["status"], "pending")
        approved = service.approve_payment("#10001")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["order_status"], "paid")

    def test_transaction_number_button_sets_submission_state(self):
        context = SimpleNamespace(user_data={})
        update = SimpleNamespace(callback_query=None, effective_user=None)

        async def run_test() -> None:
            await handle_transaction_number(update, context, "Telebirr")

        asyncio.run(run_test())
        self.assertTrue(context.user_data.get("awaiting_payment_submission"))
        self.assertEqual(context.user_data.get("payment_provider"), "Telebirr")

    def test_admin_dashboard_shows_pending_payments_and_reserved_products(self):
        PaymentService._submissions.clear()
        OrderService._orders.clear()

        order = OrderService().create_order(
            telegram_id=123,
            cart=[{"product_id": "smartphone-1", "name": "Smartphone", "price": 25000, "quantity": 1}],
            order_type="reservation",
        )
        order["order_status"] = "reserved"
        PaymentService().submit_payment(
            order_id=order["order_id"],
            customer_id=123,
            payment_method="Telebirr",
            payment_type="reservation",
            amount=12500,
            transaction_number="TX999",
        )

        self.assertTrue(any(payment["customer_id"] == 123 for payment in PaymentService().list_pending()))
        self.assertTrue(any(item["order_id"] == order["order_id"] for item in OrderService().get_reserved_product_summary()))

        with patch.object(InventoryService, "reserve_items", return_value=True):
            PaymentService().approve_payment(order["order_id"])
        self.assertEqual(OrderService().get_order(order["order_id"])["order_status"], "reserved")

    def test_admin_created_product_is_visible_to_customers(self):
        created = InventoryService().add_product({
            "category": "drugstore",
            "name": "New Admin Product",
            "description": "Visible to customers",
            "price": 250,
            "stock_quantity": 4,
            "status": "available",
            "is_active": True,
            "sizes": [],
            "colors": [],
        })

        category_items = InventoryService().list_products_by_category("drugstore")
        self.assertTrue(any(item["id"] == created["id"] for item in category_items))
        self.assertEqual(InventoryService().get_product(created["id"])["status"], "available")

    def test_admin_store_image_accepts_image_documents(self):
        message = SimpleNamespace(
            photo=None,
            document=SimpleNamespace(file_id="doc-123", mime_type="image/jpeg"),
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(message=message)
        context = SimpleNamespace(user_data={"product_creation_step": "image"})

        async def run_test() -> None:
            await __import__("ehd_shope.handlers.admin", fromlist=["admin_store_image"]).admin_store_image(update, context)

        asyncio.run(run_test())
        self.assertEqual(context.user_data["new_product_image"], "doc-123")
        self.assertEqual(context.user_data["new_product_image_type"], "document")
        self.assertEqual(context.user_data["product_creation_step"], "name")
        self.assertIn("Enter product name", message.reply_text.await_args.args[0])

    def test_product_card_downloads_document_image_before_sending_photo(self):
        product = {
            "id": "product-1",
            "category": "drugstore",
            "name": "Test item",
            "description": "Test description",
            "price": 250,
            "stock_quantity": 2,
            "image_file_id": "doc-image-id",
            "image_url": "doc-image-id",
            "image_source_type": "document",
        }
        telegram_file = SimpleNamespace(download_as_bytearray=AsyncMock(return_value=bytearray(b"image-bytes")))
        bot = SimpleNamespace(
            get_file=AsyncMock(return_value=telegram_file),
            send_photo=AsyncMock(),
        )
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(chat=SimpleNamespace(id=123)),
        )
        update = SimpleNamespace(callback_query=query, message=None)
        context = SimpleNamespace(bot=bot, user_data={})

        async def run_test() -> None:
            with patch.object(InventoryService, "get_product", return_value=product):
                await show_product_card(update, context, "product-1")

        asyncio.run(run_test())
        bot.get_file.assert_awaited_once_with("doc-image-id")
        self.assertEqual(bot.send_photo.await_args.kwargs["photo"], b"image-bytes")

    def test_product_card_falls_back_to_text_if_image_fails(self):
        product = {
            "id": "product-2",
            "category": "electronics",
            "name": "Test item",
            "description": "Test description",
            "price": 250,
            "stock_quantity": 2,
            "image_file_id": "invalid-image-id",
            "image_source_type": "photo",
        }
        bot = SimpleNamespace(
            get_file=AsyncMock(side_effect=BadRequest("invalid image")),
            send_photo=AsyncMock(side_effect=BadRequest("invalid image")),
        )
        query = SimpleNamespace(
            answer=AsyncMock(),
            message=SimpleNamespace(photo=None, chat=SimpleNamespace(id=123), reply_text=AsyncMock()),
            edit_message_text=AsyncMock(),
            edit_message_caption=AsyncMock(),
        )
        update = SimpleNamespace(callback_query=query, message=None)
        context = SimpleNamespace(bot=bot, user_data={})

        async def run_test() -> None:
            with self.assertLogs("ehd_shope.handlers.shop", level="ERROR"), patch.object(
                InventoryService,
                "get_product",
                return_value=product,
            ):
                await show_product_card(update, context, "product-2")

        asyncio.run(run_test())
        query.answer.assert_awaited_once_with()
        query.edit_message_text.assert_awaited_once()

    def test_admin_store_price_accepts_etb_values(self):
        message = SimpleNamespace(
            text="250 ETB",
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(message=message)
        context = SimpleNamespace(user_data={})

        async def run_test() -> None:
            await __import__("ehd_shope.handlers.admin", fromlist=["admin_store_price"]).admin_store_price(update, context)

        asyncio.run(run_test())
        self.assertEqual(context.user_data["new_product_price"], 250.0)
        self.assertEqual(context.user_data["product_creation_step"], "stock")
        self.assertIn("Enter product stock", message.reply_text.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
