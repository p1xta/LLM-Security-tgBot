from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Настройки приложения
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: int = 120
    
    # URL сервисов
    VALIDATOR_URL: str = os.environ.get("VALIDATOR_URL", "http://localhost:8001")
    RAG_URL: str = os.environ.get("RAG_URL", "http://localhost:8002")
    LLM_URL: str = os.environ.get("LLM_URL", "http://localhost:8003")
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()