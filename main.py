import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiohttp import web
from config import config
from handlers import router
from db import init_db

async def health_check(request):
    return web.json_response({"status": "healthy"})

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    init_db()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )
    
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Start the web server concurrently
    await start_web_server()
    
    logging.info("Bot is starting polling... (Clean Rebuild V2)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
