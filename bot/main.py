import asyncio
import logging
import uvloop
from aiogram import Bot, Dispatcher
from bot.config import config
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.handlers import commands, downloader

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    
    dp.message.middleware(ThrottlingMiddleware())
    
    dp.include_router(commands.router)
    dp.include_router(downloader.router)
    
    logging.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
