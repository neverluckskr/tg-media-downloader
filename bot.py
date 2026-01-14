import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import config
from app.handlers import common, soundcloud


async def main() -> None:
    config.validate()
    
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(common.router)
    dp.include_router(soundcloud.router)
    
    logging.info("Bot started")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )
    asyncio.run(main())
