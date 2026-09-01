import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.config import get_settings
from app.db import Database
from app.handlers import commands, media, text
from app.middleware.owner_only import OwnerOnlyMiddleware
from app.services.ai import AIService
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0-rc1"


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = get_settings()
    db = Database(settings.database_url)
    ai = AIService(settings)
    memory = MemoryService(db)

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    # Security boundary: unauthorized Telegram users stop here,
    # before handlers, DB writes, file downloads, and OpenAI calls.
    dp.update.outer_middleware(
        OwnerOnlyMiddleware(settings.owner_telegram_id)
    )

    dp.include_router(commands.router)
    dp.include_router(media.router)
    dp.include_router(text.router)

    try:
        logger.info("Starting Personal AI Assistant %s", APP_VERSION)

        logger.info("Opening PostgreSQL connection pool")
        await db.open()

        logger.info("Initializing PostgreSQL schema")
        await db.init_schema()

        if not await db.ping():
            raise RuntimeError("PostgreSQL health check failed")

        me = await bot.get_me()
        logger.info("Telegram bot connected: @%s", me.username or me.id)

        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Open Personal AI"),
                BotCommand(command="new", description="Start a fresh conversation"),
                BotCommand(command="memory", description="Show long-term memory"),
                BotCommand(command="remember", description="Save a memory manually"),
                BotCommand(command="forget", description="Delete a saved memory"),
                BotCommand(command="help", description="Show help"),
            ]
        )

        # Long polling is used; make sure an old webhook cannot block getUpdates.
        await bot.delete_webhook(drop_pending_updates=False)

        logger.info(
            "Starting Telegram long polling with model=%s",
            settings.openai_model,
        )

        await dp.start_polling(
            bot,
            db=db,
            settings=settings,
            ai=ai,
            memory=memory,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Shutting down")
        await db.close()
        await bot.session.close()
