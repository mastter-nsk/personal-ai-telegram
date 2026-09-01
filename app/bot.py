import logging
import sys

from aiogram import Bot, Dispatcher

from app.config import get_settings
from app.db import Database
from app.handlers import commands, media, text
from app.middleware.owner_only import OwnerOnlyMiddleware
from app.services.ai import AIService

logger = logging.getLogger(__name__)


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = get_settings()
    db = Database(settings.database_url)
    ai = AIService(settings)

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    dp.update.outer_middleware(
        OwnerOnlyMiddleware(settings.owner_telegram_id)
    )

    dp.include_router(commands.router)
    dp.include_router(media.router)
    dp.include_router(text.router)

    try:
        logger.info("Opening PostgreSQL connection pool")
        await db.open()

        logger.info("Initializing PostgreSQL schema")
        await db.init_schema()

        if not await db.ping():
            raise RuntimeError("PostgreSQL health check failed")

        me = await bot.get_me()
        logger.info("Telegram bot connected: @%s", me.username or me.id)

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
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Shutting down")
        await db.close()
        await bot.session.close()
