from aiogram import BaseMiddleware
from db import add_user

class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if hasattr(event, "from_user") and event.from_user:
            user = event.from_user
            await add_user(user.id, user.username, user.full_name)
        return await handler(event, data)
