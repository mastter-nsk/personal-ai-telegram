from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.db import Database
from app.services.memory import MemoryService

router = Router(name="commands")


async def _ensure_owner(message: Message, db: Database) -> dict | None:
    if message.from_user is None:
        return None

    return await db.ensure_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )


def _command_argument(message: Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


@router.message(CommandStart())
async def start_handler(message: Message, db: Database) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    await message.answer(
        "✅ Personal AI is running.\n"
        "🔐 Owner access confirmed.\n"
        "🐘 PostgreSQL is connected.\n"
        "🤖 AI chat is ready.\n"
        "🧠 Long-term memory is ready.\n\n"
        "Commands:\n"
        "/new — fresh conversation\n"
        "/memory — show saved memories\n"
        "/remember text — save a memory\n"
        "/forget ID — delete a memory"
    )


@router.message(Command("new"))
async def new_handler(message: Message, db: Database) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    await db.new_conversation(user["id"])
    await message.answer(
        "🆕 New conversation started.\n"
        "Long-term memory is preserved."
    )


@router.message(Command("memory"))
async def memory_handler(
    message: Message,
    db: Database,
    memory: MemoryService,
) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    memories = await memory.get_all(user["id"])

    if not memories:
        await message.answer(
            "🧠 Long-term memory is empty.\n"
            "Use /remember followed by a fact, or just talk to me normally."
        )
        return

    lines = ["🧠 Long-term memory:"]
    for item in memories:
        source = "manual" if item["source"] == "manual" else "auto"
        lines.append(f"{item['id']}. {item['content']} [{source}]")

    await message.answer("\n".join(lines))


@router.message(Command("remember"))
async def remember_handler(
    message: Message,
    db: Database,
    memory: MemoryService,
) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    content = _command_argument(message)
    if not content:
        await message.answer(
            "Usage:\n/remember I prefer short answers"
        )
        return

    saved, created = await memory.add_manual(user["id"], content)

    if created:
        await message.answer(
            f"🧠 Saved as memory #{saved['id']}."
        )
    else:
        await message.answer(
            f"🧠 That is already saved as memory #{saved['id']}."
        )


@router.message(Command("forget"))
async def forget_handler(
    message: Message,
    db: Database,
    memory: MemoryService,
) -> None:
    user = await _ensure_owner(message, db)
    if user is None:
        return

    argument = _command_argument(message)
    if not argument.isdigit():
        await message.answer(
            "Usage:\n/forget 3\n\n"
            "Use /memory first to see memory IDs."
        )
        return

    deleted = await memory.delete(
        user_id=user["id"],
        memory_id=int(argument),
    )

    if deleted:
        await message.answer("🗑 Memory deleted.")
    else:
        await message.answer("Memory with that ID was not found.")
