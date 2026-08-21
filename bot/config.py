from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    bot_token: str
    redis_url: str = "redis://localhost:6379/0"
    rate_limit: int = 10
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

config = Settings()
