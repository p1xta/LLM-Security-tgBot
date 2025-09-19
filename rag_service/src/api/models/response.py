from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RAGResponse(BaseModel):
    message: Optional[str] = Field(None, description="Сообщение для пользователя")
    original_request: Dict[str, Any] = Field(..., description="Исходный запрос")
    processed_at: datetime = Field(default_factory=datetime.now, description="Время обработки запроса")
    chunks: List[str] = Field(..., description="Релевантные текстовые фрагменты, найденные в документах")
    context_ids: Optional[List[str]] = Field(
        None, 
        description="Список идентификаторов документов или чанков, которые использовались"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Дополнительная информация о поиске (например, время выполнения, количество документов)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Найдено 3 релевантных документа",
                "original_request": {
                    "bucket": "documents-bucket",
                    "folder": "knowledge_base/",
                    "query": "Какие налоги должны платить ИП?",
                    "user_id": "user_123"
                },
                "processed_at": "2023-10-15T12:05:00Z",
                "chunks": [
                    "Индивидуальные предприниматели обязаны платить НДФЛ ...",
                    "Страховые взносы уплачиваются ежеквартально ...",
                    "Для применения УСН необходимо подать уведомление ..."
                ],
                "context_ids": ["doc_1_page_2", "doc_3_page_1", "doc_5_page_4"],
                "metadata": {"response_time_ms": 842, "docs_scanned": 12}
            }
        }