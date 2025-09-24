from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv


class Settings(BaseSettings):
    # Настройки приложения
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: int = 30
    load_dotenv()
    MODERATOR_URL: str = os.environ.get("LLM_URL", "localhost:8003")

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()