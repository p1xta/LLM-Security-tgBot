from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ResponseStatus(str, Enum):
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    SERVICE_UNAVAILABLE = "service_unavailable"

class ProcessResponse(BaseModel):
    """Модель ответа с результатом обработки запроса"""
    
    status: ResponseStatus = Field(..., description="Статус обработки запроса")
    message: Optional[str] = Field(None, description="Сообщение для пользователя")
    original_request: Dict[str, Any] = Field(..., description="Исходный запрос")
    processed_at: datetime = Field(default_factory=datetime.now, description="Время обработки запроса")
    context_used: Optional[List[str]] = Field(
        None, 
        description="Идентификаторы контекста, использованного для генерации ответа"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Дополнительные метаданные ответа"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Привет! У меня всё отлично, спасибо, что спросил!",
                "original_request": {
                    "user_id": 123456789,
                    "chat_id": 987654321,
                    "message_id": 123,
                    "text": "Привет, как дела?"
                },
                "processed_at": "2023-10-15T12:00:05Z",
                "context_used": ["faq_123", "knowledge_456"],
                "metadata": {"response_time_ms": 1200}
            }
        }