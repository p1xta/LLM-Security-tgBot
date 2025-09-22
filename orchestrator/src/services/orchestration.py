from clients.validator_client import ValidatorClient
from clients.rag_client import RAGClient
from clients.llm_client import LLMClient
from utils.retry import with_retry
from utils.circuit_breaker import with_circuit_breaker
from exceptions.specific import ValidationFailedError

class OrchestrationService:
    def __init__(self):
        self.validator_client = ValidatorClient()
        self.rag_client = RAGClient()
        self.llm_client = LLMClient()
    
    @with_retry(max_attempts=3, delay=1)
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
    async def validate_request(self, payload: dict):
        response = await self.validator_client.validate(payload)
        if not response.get("is_valid", False):
            raise ValidationFailedError("Request validation failed")
        return response
    
    @with_retry(max_attempts=3, delay=1)
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
    async def retrieve_context(self, payload: dict):
        return await self.rag_client.retrieve(payload)
    
    @with_retry(max_attempts=3, delay=1)
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
    async def generate_response(self, context: dict):
        return await self.llm_client.generate(context)
    
    async def __call__(self, payload: dict):
        # Валидация запроса
        await self.validate_request(payload)
        
        
        # Получение контекста
        context = await self.retrieve_context({
                "bucket": "tgbot-storage",
                "query": payload['text']
            })
        
        chunks = context['chunks']
        context_chunks = "\n\n".join(chunks)
        # Генерация ответа
        response = await self.generate_response({
            "user_prompt": payload['text'], 
            "system_prompt": "Ты — корпоративный ассистент. Отвечай строго по документам. "
                            "Если информации нет — скажи 'В документах не указано'.\n\n"
                            f"Контекст из документов:\n{context_chunks}"
            }
        )
        
        return {
                "status": "success",
                "message": response['message'],
                "original_request": payload
            }

# Создаем экземпляр сервиса для dependency injection
orchestrate_processing = OrchestrationService()