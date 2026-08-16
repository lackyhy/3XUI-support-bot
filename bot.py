import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from core.env_setup import ensure_env_file
ensure_env_file()

import config
from middlewares.auth import AdminMiddleware
from handlers import start, setup, server, inbounds, clients

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("3x-ui-bot")

async def create_bot_instance() -> Bot:
    if not config.BOT_PROXY:
        return Bot(token=config.BOT_TOKEN)

    logger.info(f"Connecting to Telegram via Proxy: {config.BOT_PROXY}")
    from aiogram.client.session.aiohttp import AiohttpSession
    session = AiohttpSession(proxy=config.BOT_PROXY)
    return Bot(token=config.BOT_TOKEN, session=session)

async def main():
    logger.info("Initializing 3x-ui Management Bot...")
    logger.info(f"Authorized Admin ID: {config.ADMIN_ID}")
    if config.BOT_PROXY:
        logger.info(f"Bot Proxy: {config.BOT_PROXY}")
    if config.PANEL_PROXY:
        logger.info(f"Panel Proxy: {config.PANEL_PROXY}")
    
    bot = await create_bot_instance()
    dp = Dispatcher(storage=MemoryStorage())

    # Attach Authorization Middleware
    admin_middleware = AdminMiddleware()
    dp.message.middleware(admin_middleware)
    dp.callback_query.middleware(admin_middleware)

    # Register Routers
    dp.include_router(start.router)
    dp.include_router(setup.router)
    dp.include_router(server.router)
    dp.include_router(inbounds.router)
    dp.include_router(clients.router)

    # Drop pending updates and start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
