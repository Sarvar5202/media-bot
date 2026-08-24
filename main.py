import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiohttp import web
from config import config
from handlers import router, cache_cleanup_task
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

from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

async def setup_bot_commands(bot: Bot):
    public_commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va ma'lumot"),
        BotCommand(command="language", description="Tilni o'zgartirish / Язык / Language"),
    ]
    await bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())
    
    if config.admin_id:
        admin_commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="help", description="Yordam va ma'lumot"),
            BotCommand(command="stats", description="Bot statistikasi"),
            BotCommand(command="users", description="Foydalanuvchilar ro'yxati"),
            BotCommand(command="broadcast", description="Xabar tarqatish (/broadcast <xabar>)"),
            BotCommand(command="user_info", description="Foydalanuvchi ma'lumoti (/user_info <id>)"),
        ]
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=config.admin_id))
        except Exception as e:
            logging.error(f"Failed to set admin commands: {e}")

async def main():
    await init_db()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )
    
    from aiogram.client.session.aiohttp import AiohttpSession
    from aiogram.client.telegram import TelegramAPIServer
    
    session = None
    if config.local_api_server_url:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(config.local_api_server_url, is_local=True)
        )
        logging.info(f"Using Local Telegram Bot API Server: {config.local_api_server_url}")
        
    bot = Bot(token=config.bot_token, session=session)
    dp = Dispatcher()
    
    from middlewares import UserTrackingMiddleware
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
    dp.include_router(router)
    
    await setup_bot_commands(bot)
    
    # Start the web server concurrently
    await start_web_server()
    
    # Start cache cleanup task
    asyncio.create_task(cache_cleanup_task())
    
    logging.info("Deleting webhook and dropping pending updates to prevent conflicts...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logging.warning(f"Failed to delete webhook (safe to ignore): {e}")
    
    logging.info("Bot is starting polling... (Clean Rebuild V3)")
    while True:
        try:
            await dp.start_polling(bot, handle_signals=False)
            break
        except Exception as e:
            err_msg = str(e).lower()
            if "conflict" in err_msg or "terminated by other getupdates request" in err_msg:
                logging.error("Conflict error. Another instance is polling. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            elif "network" in err_msg or "timeout" in err_msg or "clientoserror" in err_msg:
                logging.error(f"Network error during polling: {e}. Retrying in 5s...")
                await asyncio.sleep(5)
            else:
                logging.error(f"Unexpected polling error: {e}. Retrying in 5s...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
