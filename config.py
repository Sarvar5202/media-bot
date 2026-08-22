import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    bot_token: str = os.getenv("BOT_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    admin_id: Optional[int] = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") and os.getenv("ADMIN_ID").isdigit() else None
    local_api_server_url: Optional[str] = os.getenv("LOCAL_API_SERVER_URL")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

config = Settings()
if not config.bot_token:
    config.bot_token = os.getenv("BOT_TOKEN", "")
if not config.database_url:
    config.database_url = os.getenv("DATABASE_URL", "")
