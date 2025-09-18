from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Настройки приложения
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: int = 30
    
    # URL сервисов
    VALIDATOR_URL: str = "http://validator:8000"
    RAG_URL: str = "http://rag:8000"
    LLM_URL: str = "http://llm:8000"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()