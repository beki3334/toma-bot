import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import BOT_TOKEN, PROXY_URL, DEEZER_ARL
from database import init_db
from handlers import all_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot: Bot = None


async def on_startup():
    await init_db()
    logger.info("Database initialized!")
    if DEEZER_ARL:
        from deezer_stream import init_deezer
        init_deezer(DEEZER_ARL)
        logger.info("Deezer full track streaming enabled!")
    else:
        logger.warning("No DEEZER_ARL set - using 30s previews only")


async def main():
    global bot
    if PROXY_URL:
        from aiogram.client.session.aiohttp import AiohttpSession
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
        logger.info(f"Using proxy: {PROXY_URL}")
    else:
        bot = Bot(token=BOT_TOKEN)
        logger.info("No proxy configured")

    dp = Dispatcher()
    for router in all_routers:
        dp.include_router(router)

    dp.startup.register(on_startup)
    logger.info("Music bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
