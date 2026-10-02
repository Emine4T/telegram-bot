from telegram import InlineKeyboardMarkup, Update
from telegram.error import BadRequest


async def edit_callback_message(
    update: Update,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    message = query.message
    try:
        if any(
            getattr(message, media_type, None)
            for media_type in ("photo", "video", "animation", "document", "audio")
        ):
            await query.edit_message_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        else:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
    except BadRequest:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)