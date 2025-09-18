from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Настройки приложения
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: int = 30
    MODERATOR_URL: str = "localhost:8002"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()