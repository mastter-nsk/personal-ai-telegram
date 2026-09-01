import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.config import Settings
from app.db import Database
from app.services.ai import AIService

router = Router(name="text")
logger = logging.getLogger(__name__)


def split_for_telegram(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit

        chunk = remaining[:cut].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks


@router.message(F.text & ~F.text.startswith("/"))
async def text_handler(
    message: Message,
    db: Database,
    settings: Settings,
    ai: AIService,
) -> None:
    if message.from_user is None or not message.text:
        return

    user_text = message.text.strip()
    if not user_text:
        return

    user = await db.ensure_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )
    conversation_id = await db.get_active_conversation_id(user["id"])

    history = await db.get_recent_messages(
        conversation_id=conversation_id,
        limit=settings.context_messages,
    )

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    try:
        answer = await ai.reply(history=history, user_text=user_text)
    except Exception:
        logger.exception("OpenAI request failed")
        await message.answer(
            "⚠️ I couldn't reach the AI service. Please try again in a moment."
        )
        return

    await db.save_exchange(
        conversation_id=conversation_id,
        user_text=user_text,
        assistant_text=answer,
    )

    for chunk in split_for_telegram(answer):
        await message.answer(chunk)
