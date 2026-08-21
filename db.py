import asyncpg
import logging
from config import config

pool = None

async def init_db():
    global pool
    if not config.database_url:
        logging.warning("DATABASE_URL is not set. Database features will be disabled.")
        return
    
    try:
        pool = await asyncpg.create_pool(config.database_url)
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")

async def add_user(user_id: int, username: str = None):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, is_active, last_active) 
                VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE 
                SET username = EXCLUDED.username, 
                    is_active = TRUE,
                    last_active = CURRENT_TIMESTAMP
            """, user_id, username)
    except Exception as e:
        logging.error(f"Error adding user: {e}")

async def get_stats() -> dict:
    if not pool: return {"total": 0, "active": 0, "new_24h": 0}
    try:
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM users")
            active = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
            new_24h = await conn.fetchval("SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '24 HOURS'")
            return {"total": total, "active": active, "new_24h": new_24h}
    except Exception as e:
        logging.error(f"Error getting stats: {e}")
        return {"total": 0, "active": 0, "new_24h": 0}

async def get_user_info(user_id: int) -> dict:
    if not pool: return None
    try:
        async with pool.acquire() as conn:
            record = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(record) if record else None
    except Exception as e:
        logging.error(f"Error getting user info: {e}")
        return None

async def set_user_inactive(user_id: int):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET is_active = FALSE WHERE user_id = $1", user_id)
    except Exception as e:
        logging.error(f"Error setting user inactive: {e}")

async def get_all_active_users() -> list:
    if not pool: return []
    try:
        async with pool.acquire() as conn:
            records = await conn.fetch("SELECT user_id FROM users WHERE is_active = TRUE")
            return [r['user_id'] for r in records]
    except Exception as e:
        logging.error(f"Error getting active users: {e}")
        return []

async def get_all_users(limit: int = 50) -> list:
    if not pool: return []
    try:
        async with pool.acquire() as conn:
            records = await conn.fetch("SELECT user_id, username FROM users ORDER BY created_at DESC LIMIT $1", limit)
            return [(r['user_id'], r['username']) for r in records]
    except Exception as e:
        logging.error(f"Error getting all users: {e}")
        return []
