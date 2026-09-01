from aiogram import F, Router
from aiogram.types import Message

router = Router(name="text")


@router.message(F.text)
async def temporary_text_handler(message: Message) -> None:
    await message.answer(
        "Core is working. AI chat is not connected yet."
    )
