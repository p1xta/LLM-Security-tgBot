from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ValidationRequest(BaseModel):
    """Модель запроса для валидации"""
    
    user_id: int = Field(..., description="ID пользователя в Telegram")
    chat_id: int = Field(..., description="ID чата в Telegram")
    message_id: int = Field(..., description="ID сообщения")
    text: str = Field(..., min_length=1, max_length=4096, description="Текст сообщения пользователя")
    timestamp: str = Field(default_factory="00.00.00", description="Время получения сообщения")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Дополнительные метаданные запроса"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 123456789,
                "chat_id": 987654321,
                "message_id": 123,
                "text": "Привет, как дела?",
                "timestamp": "2023-10-15T12:00:00Z",
                "metadata": {"language": "ru"}
            }
        }