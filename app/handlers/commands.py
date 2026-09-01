from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db import Database

router = Router(name="commands")


@router.message(CommandStart())
async def start_handler(message: Message, db: Database) -> None:
    if message.from_user is None:
        return

    await db.ensure_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )

    await message.answer(
        "✅ Personal AI is running.\n"
        "🔐 Owner access confirmed.\n"
        "🐘 PostgreSQL is connected.\n\n"
        "OpenAI chat will be added in the next step."
    )
