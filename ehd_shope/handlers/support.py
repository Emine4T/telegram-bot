from telegram import Update
from telegram.ext import ContextTypes

try:
    from ehd_shope.services.ai_support_service import (
        CONFIGURATION_FALLBACK,
        generate_support_reply,
        is_support_configured,
    )
except ImportError:
    from services.ai_support_service import CONFIGURATION_FALLBACK, generate_support_reply, is_support_configured


MAX_SUPPORT_HISTORY_MESSAGES = 10
MAX_SUPPORT_INPUT_LENGTH = 2000


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_support_configured():
        if update.message:
            await update.message.reply_text(CONFIGURATION_FALLBACK)
        return

    context.user_data["support_chat_active"] = True
    context.user_data["support_history"] = []
    if update.message:
        await update.message.reply_text(
            "AI shop support is ready. Ask a question in English or Amharic. "
            "Messages are sent to OpenAI to generate replies. Send /endsupport to leave. "
            "Do not send passwords, verification codes, or payment credentials. / "
            "የAI ድጋፍ ዝግጁ ነው። ጥያቄዎን በአማርኛ ወይም በእንግሊዝኛ ይጠይቁ። "
            "መልዕክቶችዎ መልስ ለማዘጋጀት ወደ OpenAI ይላካሉ። ለመውጣት /endsupport ይላኩ። "
            "የይለፍ ቃል፣ የማረጋገጫ ኮድ ወይም የክፍያ መረጃ አይላኩ።"
        )


async def end_support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("support_chat_active", None)
    context.user_data.pop("support_history", None)
    if update.message:
        await update.message.reply_text("Support chat ended. / የድጋፍ ውይይቱ ተጠናቋል።")


async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return

    text = update.message.text.strip()
    if not text:
        return

    history = context.user_data.setdefault("support_history", [])
    history.append({"role": "user", "content": text[:MAX_SUPPORT_INPUT_LENGTH]})
    reply = await generate_support_reply(history)
    history.append({"role": "assistant", "content": reply})
    del history[:-MAX_SUPPORT_HISTORY_MESSAGES]
    await update.message.reply_text(reply)
