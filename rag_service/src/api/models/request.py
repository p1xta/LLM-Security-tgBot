from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


class RAGRequest(BaseModel):
    """Запрос к RAG сервису"""
    
    bucket: str = Field(..., description="Название S3 bucket")
    folder: Optional[str] = Field("", description="Папка в bucket для поиска файлов")
    query: str = Field(..., description="Запрос пользователя")
    user_id: Optional[str] = Field(None, description="Идентификатор пользователя")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные запроса")
    
    class Config:
        schema_extra = {
            "example": {
                "bucket": "documents-bucket",
                "folder": "knowledge_base/",
                "query": "Какие налоги должны платить ИП?",
                "user_id": "user_123",
                "metadata": {"request_id": "req_987"}
            }
        }


class RAGUploadRequest(BaseModel):
    """Запрос на сохранение файлов в RAG сервис"""

    bucket: str = Field(..., description="Название S3 bucket")
    user_id: str = Field(..., description="Идентификатор пользователя")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Дополнительные метаданные")

    class Config:
        schema_extra = {
            "example": {
                "bucket": "documents-bucket",
                "user_id": "user_123",
                "metadata": {"request_id": "req_987"}
            }
        }