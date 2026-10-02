import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from ehd_shope.bot import handle_product_form_text
from ehd_shope.handlers.support import end_support_command, handle_support_message, support_command
from ehd_shope.services import ai_support_service


class AISupportTests(unittest.TestCase):
    def test_support_command_starts_fresh_session(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(message=message)
        context = SimpleNamespace(user_data={"support_history": [{"role": "user", "content": "old"}]})

        with patch("ehd_shope.handlers.support.is_support_configured", return_value=True):
            asyncio.run(support_command(update, context))

        self.assertTrue(context.user_data["support_chat_active"])
        self.assertEqual(context.user_data["support_history"], [])
        message.reply_text.assert_awaited_once()

    def test_support_command_does_not_start_without_api_key(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(message=message)
        context = SimpleNamespace(user_data={})

        with patch("ehd_shope.handlers.support.is_support_configured", return_value=False):
            asyncio.run(support_command(update, context))

        self.assertNotIn("support_chat_active", context.user_data)
        message.reply_text.assert_awaited_once()

    def test_ending_support_clears_session(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(message=message)
        context = SimpleNamespace(
            user_data={"support_chat_active": True, "support_history": [{"role": "user", "content": "hi"}]}
        )

        asyncio.run(end_support_command(update, context))

        self.assertNotIn("support_chat_active", context.user_data)
        self.assertNotIn("support_history", context.user_data)
        message.reply_text.assert_awaited_once()

    def test_support_message_uses_ai_and_limits_history(self):
        message = SimpleNamespace(text="Do you sell shoes?", reply_text=AsyncMock())
        update = SimpleNamespace(message=message)
        history = [{"role": "user", "content": "previous"}] * 10
        context = SimpleNamespace(user_data={"support_history": history})

        with patch(
            "ehd_shope.handlers.support.generate_support_reply",
            new_callable=AsyncMock,
            return_value="Please check /shop for current products.",
        ) as generate_reply:
            asyncio.run(handle_support_message(update, context))

        generate_reply.assert_awaited_once()
        self.assertLessEqual(len(context.user_data["support_history"]), 10)
        self.assertEqual(context.user_data["support_history"][-1]["role"], "assistant")
        message.reply_text.assert_awaited_once_with("Please check /shop for current products.")

    def test_payment_submission_takes_precedence_over_support_mode(self):
        message = SimpleNamespace(text="TXN-123")
        update = SimpleNamespace(message=message)
        context = SimpleNamespace(user_data={"awaiting_payment_submission": True, "support_chat_active": True})

        with patch("ehd_shope.bot.submit_payment_evidence", new_callable=AsyncMock) as submit_payment, patch(
            "ehd_shope.bot.handle_support_message", new_callable=AsyncMock
        ) as handle_support:
            asyncio.run(handle_product_form_text(update, context))

        self.assertEqual(context.user_data["transaction_number"], "TXN-123")
        submit_payment.assert_awaited_once_with(update, context)
        handle_support.assert_not_awaited()

    def test_missing_api_key_returns_friendly_fallback(self):
        with patch.object(ai_support_service, "OPENAI_API_KEY", ""):
            reply = asyncio.run(ai_support_service.generate_support_reply([]))

        self.assertIn("not configured", reply)

    def test_configured_api_uses_bounded_history_and_system_prompt(self):
        history = [{"role": "user", "content": "Question"}] * 12
        with patch.object(ai_support_service, "OPENAI_API_KEY", "test-key"), patch.object(
            ai_support_service,
            "_request_completion",
            new_callable=AsyncMock,
            return_value="Answer",
        ) as request:
            reply = asyncio.run(ai_support_service.generate_support_reply(history))

        self.assertEqual(reply, "Answer")
        messages = request.await_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Never request", messages[0]["content"])
        self.assertEqual(len(messages), 11)

    def test_openai_client_receives_model_and_request_limits(self):
        completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=" Answer "))])
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        create_completion = AsyncMock(return_value=completion)
        client.chat.completions.create = create_completion
        messages = [{"role": "user", "content": "Question"}]

        with patch.object(ai_support_service, "OPENAI_API_KEY", "test-key"), patch.object(
            ai_support_service, "OPENAI_MODEL", "test-model"
        ), patch("openai.AsyncOpenAI", return_value=client) as client_factory:
            answer = asyncio.run(ai_support_service._request_completion(messages))

        self.assertEqual(answer, "Answer")
        client_factory.assert_called_once_with(api_key="test-key", timeout=20.0)
        create_completion.assert_awaited_once_with(model="test-model", messages=messages, max_tokens=350)


if __name__ == "__main__":
    unittest.main()