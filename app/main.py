"""
Application entry point.

Initialises configuration, logging, database, and starts the Telegram bot
using aiogram's long-polling mechanism.

Run with:
    python -m app.main
"""
import asyncio
import sys
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import admin, start, student, teacher
from app.bot.middlewares.auth import AuthMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.config import get_settings
from app.database.connection import init_db
from app.utils.logger import configure_logging, get_logger


async def health_check(request: web.Request) -> web.Response:
    """Simple health check endpoint for Render."""
    return web.Response(text="OK")


async def start_health_server() -> web.AppRunner:
    """Start a minimal HTTP server so Render detects an open port."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    return runner


async def main() -> None:
    settings = get_settings()

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #
    configure_logging(
        log_level=settings.log_level,
        environment=settings.environment,
    )
    logger = get_logger(__name__)
    logger.info(
        "application_starting",
        environment=settings.environment,
        log_level=settings.log_level,
    )

    # ------------------------------------------------------------------ #
    # Health check server (required for Render Web Service)               #
    # ------------------------------------------------------------------ #
    runner = await start_health_server()
    logger.info("health_server_started", port=10000)

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #
    logger.info("connecting_to_database")
    await init_db()
    logger.info("database_ready")

    # ------------------------------------------------------------------ #
    # Bot & dispatcher                                                     #
    # ------------------------------------------------------------------ #
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ------------------------------------------------------------------ #
    # Middlewares                                                          #
    # ------------------------------------------------------------------ #
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(RateLimitMiddleware())
    dp.update.outer_middleware(AuthMiddleware())

    # ------------------------------------------------------------------ #
    # Routers                                                              #
    # ------------------------------------------------------------------ #
    dp.include_router(start.router)
    dp.include_router(student.router)
    dp.include_router(teacher.router)
    dp.include_router(admin.router)

    # ------------------------------------------------------------------ #
    # Start polling                                                        #
    # ------------------------------------------------------------------ #
    bot_info = await bot.get_me()
    logger.info(
        "bot_starting",
        username=bot_info.username,
        bot_id=bot_info.id,
    )

    admin_ids = settings.get_admin_telegram_ids()
    if not admin_ids:
        logger.warning(
            "no_admin_ids_configured",
            hint="Set ADMIN_TELEGRAM_IDS in .env to bootstrap admin access.",
        )

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("bot_stopping")
        await bot.session.close()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        sys.exit(0)
