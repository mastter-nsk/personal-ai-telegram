from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.db import Database

router = Router(name="commands")


async def _ensure_owner(message: Message, db: Database) -> dict | None:
    if message.from_user is None:
        return None
    return await db.ensure_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )


@router.message(CommandStart())
async def start_handler(message: Message, db: Database) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    await message.answer(
        "✅ Personal AI is running.\n"
        "🔐 Owner access confirmed.\n"
        "🐘 PostgreSQL is connected.\n"
        "🤖 AI chat is ready.\n\n"
        "Send me a message or use /new to start a fresh conversation."
    )


@router.message(Command("new"))
async def new_handler(message: Message, db: Database) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    await db.new_conversation(user["id"])
    await message.answer("🆕 New conversation started.")
