import base64
import logging
import mimetypes
from io import BytesIO
from pathlib import Path

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from app.config import Settings
from app.db import Database
from app.handlers.text import process_user_text, split_for_telegram
from app.services.ai import AIService
from app.services.memory import MemoryService

router = Router(name="media")
logger = logging.getLogger(__name__)

MAX_TELEGRAM_DOWNLOAD_BYTES = 20 * 1024 * 1024

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".txt",
    ".md",
    ".json",
    ".html",
    ".xml",
    ".doc",
    ".docx",
    ".rtf",
    ".odt",
    ".ppt",
    ".pptx",
    ".csv",
    ".tsv",
    ".xls",
    ".xlsx",
}

MIME_OVERRIDES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".html": "text/html",
    ".xml": "text/xml",
    ".doc": "application/msword",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".csv": "text/csv",
    ".tsv": "text/tsv",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
}


async def _owner_state(
    message: Message,
    db: Database,
    settings: Settings,
    memory: MemoryService,
) -> tuple[dict, int, list[dict], str]:
    if message.from_user is None:
        raise ValueError("Telegram update has no user.")

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

    memories = await memory.get_all(user["id"])
    memory_text = memory.format_for_prompt(memories)

    return user, conversation_id, history, memory_text


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


@router.message(F.photo)
async def photo_handler(
    message: Message,
    db: Database,
    settings: Settings,
    ai: AIService,
    memory: MemoryService,
) -> None:
    if message.from_user is None or not message.photo:
        return

    photo = message.photo[-1]

    if (
        photo.file_size is not None
        and photo.file_size > MAX_TELEGRAM_DOWNLOAD_BYTES
    ):
        await message.answer(
            "⚠️ This image is too large to download through Telegram Bot API."
        )
        return

    prompt = (message.caption or "").strip()
    if not prompt:
        prompt = (
            "Analyze this image. Describe what is important and answer "
            "as a helpful personal assistant."
        )

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    buffer = BytesIO()

    try:
        await message.bot.download(
            photo,
            destination=buffer,
        )
        image_bytes = buffer.getvalue()

        if not image_bytes:
            raise ValueError("Telegram returned an empty image file.")

        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        image_data_url = f"data:image/jpeg;base64,{image_base64}"

        user, conversation_id, history, memory_text = await _owner_state(
            message=message,
            db=db,
            settings=settings,
            memory=memory,
        )

        answer = await ai.reply_with_image(
            history=history,
            user_text=prompt,
            image_data_url=image_data_url,
            memory_text=memory_text,
            save_memory=lambda content: memory.add_auto(
                user["id"],
                content,
            ),
        )

        await db.save_exchange(
            conversation_id=conversation_id,
            user_text=f"[Image] {prompt}",
            assistant_text=answer,
        )

    except Exception:
        logger.exception("Image analysis failed")
        await message.answer(
            "⚠️ I couldn't analyze that image. Please try another image."
        )
        return
    finally:
        buffer.close()

    for chunk in split_for_telegram(answer):
        await message.answer(chunk)


@router.message(F.document)
async def document_handler(
    message: Message,
    db: Database,
    settings: Settings,
    ai: AIService,
    memory: MemoryService,
) -> None:
    if message.from_user is None or message.document is None:
        return

    document = message.document
    filename = document.file_name or "document"
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        await message.answer(
            "⚠️ Unsupported document type.\n"
            "Supported: PDF, TXT, Markdown, JSON, HTML, XML, "
            "DOC/DOCX, RTF, ODT, PPT/PPTX, CSV/TSV, XLS/XLSX."
        )
        return

    if (
        document.file_size is not None
        and document.file_size > MAX_TELEGRAM_DOWNLOAD_BYTES
    ):
        await message.answer(
            "⚠️ This document is too large. "
            "Telegram Bot API download limit is 20 MB."
        )
        return

    prompt = (message.caption or "").strip()
    if not prompt:
        prompt = (
            "Analyze this document and give me a concise summary of the key "
            "information. Mention anything important, unusual, or actionable."
        )

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
    )

    buffer = BytesIO()

    try:
        await message.bot.download(
            document,
            destination=buffer,
        )
        file_bytes = buffer.getvalue()

        if not file_bytes:
            raise ValueError("Telegram returned an empty document.")

        mime_type = (
            MIME_OVERRIDES.get(extension)
            or document.mime_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )

        file_base64 = base64.b64encode(file_bytes).decode("ascii")
        file_data_url = f"data:{mime_type};base64,{file_base64}"

        user, conversation_id, history, memory_text = await _owner_state(
            message=message,
            db=db,
            settings=settings,
            memory=memory,
        )

        answer = await ai.reply_with_file(
            history=history,
            user_text=prompt,
            filename=filename,
            file_data_url=file_data_url,
            memory_text=memory_text,
            save_memory=lambda content: memory.add_auto(
                user["id"],
                content,
            ),
        )

        await db.save_exchange(
            conversation_id=conversation_id,
            user_text=f"[File: {filename}] {prompt}",
            assistant_text=answer,
        )

    except Exception:
        logger.exception("Document analysis failed: %s", filename)
        await message.answer(
            "⚠️ I couldn't analyze that document. "
            "Check the file type and try again."
        )
        return
    finally:
        buffer.close()

    for chunk in split_for_telegram(answer):
        await message.answer(chunk)
