from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.services.cache import redis_client
from bot.config import config

class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        key = f"rate_limit:{user_id}"
        
        current = await redis_client.get(key)
        if current and int(current) >= config.rate_limit:
            # We don't reply directly here to avoid spamming the user if they spam the bot.
            # But we could optionally reply once.
            if int(current) == config.rate_limit:
                await event.reply("⚠️ Too many requests! Please wait a minute.")
                
            # Still increment to penalize spam
            await redis_client.incr(key)
            return
            
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60) # reset every 60 seconds
        await pipe.execute()
        
        return await handler(event, data)
