import logging
from io import BytesIO

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.config import Settings
from app.db import Database
from app.handlers.text import process_user_text
from app.services.ai import AIService
from app.services.memory import MemoryService

router = Router(name="media")
logger = logging.getLogger(__name__)

MAX_TELEGRAM_DOWNLOAD_BYTES = 20 * 1024 * 1024


@router.message(F.voice)
async def voice_handler(
    message: Message,
    db: Database,
    settings: Settings,
    ai: AIService,
    memory: MemoryService,
) -> None:
    if message.voice is None:
        return

    if (
        message.voice.file_size is not None
        and message.voice.file_size > MAX_TELEGRAM_DOWNLOAD_BYTES
    ):
        await message.answer(
            "⚠️ This voice message is too large to download through Telegram Bot API."
        )
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    buffer = BytesIO()

    try:
        await message.bot.download(
            message.voice,
            destination=buffer,
        )
        audio_bytes = buffer.getvalue()

        if not audio_bytes:
            raise ValueError("Telegram returned an empty voice file.")

        transcript = await ai.transcribe_voice(audio_bytes)
    except Exception:
        logger.exception("Voice transcription failed")
        await message.answer(
            "⚠️ I couldn't recognize that voice message. Please try again."
        )
        return
    finally:
        buffer.close()

    await process_user_text(
        message=message,
        user_text=transcript,
        db=db,
        settings=settings,
        ai=ai,
        memory=memory,
    )
