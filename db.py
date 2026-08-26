import asyncpg
import logging
from config import config

pool = None

async def init_db():
    global pool
    db_url = config.database_url
    if not db_url:
        logging.warning("DATABASE_URL is not set. Falling back to SQLite...")
        try:
            from sqlite_mock import SQLitePool
            pool = SQLitePool()
            logging.info("SQLite fallback database initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize SQLite fallback: {e}")
            return
    else:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            pool = await asyncpg.create_pool(db_url, ssl=ctx)
            logging.info("Connected to PostgreSQL database successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize PostgreSQL: {e}. Falling back to SQLite...")
            try:
                from sqlite_mock import SQLitePool
                pool = SQLitePool()
                logging.info("SQLite fallback database initialized successfully.")
            except Exception as e2:
                logging.error(f"Failed to initialize SQLite fallback: {e2}")
                return
                
    if pool:
        try:
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
                try:
                    await conn.execute("ALTER TABLE users ADD COLUMN lang VARCHAR(10) DEFAULT 'uz'")
                except Exception:
                    pass
                
                try:
                    await conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
                except Exception:
                    pass
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS platform_stats (
                        platform VARCHAR(50) PRIMARY KEY,
                        downloads BIGINT DEFAULT 0
                    )
                """)
        except Exception as e:
            logging.error(f"Failed to run database migrations: {e}")

async def add_user(user_id: int, username: str = None, full_name: str = None):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, full_name, is_active, last_active) 
                VALUES ($1, $2, $3, TRUE, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE 
                SET username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    is_active = TRUE,
                    last_active = CURRENT_TIMESTAMP
            """, user_id, username, full_name)
    except Exception as e:
        logging.error(f"Error adding user: {e}")

async def set_user_language(user_id: int, lang: str):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("UPDATE users SET lang = $1 WHERE user_id = $2", lang, user_id)
    except Exception as e:
        logging.error(f"Error setting language: {e}")

async def get_user_language(user_id: int) -> str:
    if not pool: return 'uz'
    try:
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT lang FROM users WHERE user_id = $1", user_id)
            return val if val else 'uz'
    except Exception as e:
        logging.error(f"Error getting language: {e}")
        return 'uz'

async def increment_platform_stat(platform: str):
    if not pool: return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO platform_stats (platform, downloads) 
                VALUES ($1, 1)
                ON CONFLICT (platform) DO UPDATE 
                SET downloads = platform_stats.downloads + 1
            """, platform)
    except Exception as e:
        logging.error(f"Error incrementing platform stat: {e}")

async def get_platform_stats() -> dict:
    if not pool: return {}
    try:
        async with pool.acquire() as conn:
            records = await conn.fetch("SELECT platform, downloads FROM platform_stats ORDER BY downloads DESC")
            return {r['platform']: r['downloads'] for r in records}
    except Exception as e:
        logging.error(f"Error getting platform stats: {e}")
        return {}

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

async def get_all_users() -> list:
    if not pool: return []
    try:
        async with pool.acquire() as conn:
            records = await conn.fetch("SELECT user_id, username, full_name, created_at FROM users ORDER BY created_at DESC")
            return [dict(r) for r in records]
    except Exception as e:
        logging.error(f"Error getting all users: {e}")
        return []
