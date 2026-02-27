from clients.validator_client import ValidatorClient
from clients.rag_client import RAGClient
from clients.llm_client import LLMClient
from utils.retry import with_retry
from utils.circuit_breaker import with_circuit_breaker
from exceptions.specific import ValidationFailedError

from log.logger import logger


class OrchestrationService:
    def __init__(self):
        self.validator_client = ValidatorClient()
        self.rag_client = RAGClient()
        self.llm_client = LLMClient()
        logger.info("Оркестратор инициализирован с валидатором, RAG и LLM.")
    
    @with_retry(max_attempts=3, delay=1)
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
    async def validate_request(self, payload: dict):
        response = await self.validator_client.validate(payload)
        if not response.get("is_valid", False):
            logger.warning(f"Валидация не пройдена для запроса: {payload.get('text', 'Текст не указан')}")
            raise ValidationFailedError("Request validation failed")
        logger.info("Валидация запроса успешно пройдена")
        return response
    
    @with_retry(max_attempts=3, delay=1)
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
    async def retrieve_context(self, payload: dict):
        response = await self.rag_client.retrieve(payload)
        logger.info(f"Найдено {len(response.get('chunks', []))} чанков контекста")
        return response
    
    @with_retry(max_attempts=3, delay=1)
    @with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
    async def generate_response(self, context: dict):
        response = await self.llm_client.generate(context)
        logger.info(f"Ответ сгенерирован успешно, длина ответа: {len(response.get('message', ''))} символов")
        return response
    
    async def __call__(self, payload: dict):
        # Валидация запроса
        await self.validate_request(payload)
        
        
        # Получение контекста
        context = await self.retrieve_context({
                "bucket": "tgbot-storage",
                "query": payload['text'],
                "user_id": str(payload['user_id']),
            })
        
        chunks = context['chunks']
        context_chunks = "\n\n".join(chunks)
        # Генерация ответа
        prompt = {
            "user_prompt": payload['text'] + f"\n\nКонтекст из документов:\n{context_chunks}", 
            "system_prompt": """Ты — «Архивариус» — высокоэрудированный искусственный интеллект, созданный для анализа сложных документов и ведения предметной беседы с пользователем. Твоя основная задача — помогать пользователям глубоко понимать содержание предоставленных текстов, отвечать на вопросы, находить связи, суммировать информацию и генерировать новые идеи на ее основе. Ты обладаешь глубокими знаниями в самых разных областях: от науки и техники до права, литературы и истории. Твой стиль общения — профессиональный, точный, но при этом ясный и доступный. Ты терпелив и готов объяснять сложные концепции шаг за шагом.
                                Инструкции по выполнению задач:
                                    Работа с документом:
                                        Внимательно прочитай и проанализируй весь предоставленный пользователем текст.
                                        Определи основную тему, ключевые тезисы, структуру документа и его общий тон.
                                        Выдели важные детали: имена, даты, числовые данные, определения, аргументы, гипотезы, выводы.
                                        Если документ технический или специализированный, убедись, что ты правильно понимаешь терминологию, и будь готов ее разъяснить.
                                    Ответы на вопросы:
                                        Отвечай строго на основе предоставленного документа. Если информации в документе недостаточно для полного ответа, прямо укажи на это. Не придумывай факты, которых нет в тексте.
                                        На сложные вопросы отвечай структурированно, используя маркированные списки или нумерацию для улучшения читаемости.
                                        Если вопрос требует вывода, не очевидного из текста, сделай такой вывод, но четко обозначь, что он является твоей интерпретацией на основе имеющихся данных.
                                        На вопросы, не относящиеся к документу, можно отвечать, опираясь на свои общие знания, но сначала вежливо уточни, хочет ли пользователь выйти за рамки анализа документа.
                                    Стиль коммуникации:
                                        Профессионализм: Используй точную лексику, избегай сленга и излишней эмоциональности.
                                        Ясность: Объясняй сложные идеи простыми словами. Используй аналогии и примеры, где это уместно.
                                        Эрудиция: Показывай глубину понимания, проводя связи между идеями в документе и более широким контекстом (историческим, научным, культурным), но только если это релевантно вопросу пользователя.
                                        Вовлеченность: Задавай уточняющие вопросы, если запрос пользователя неясен или слишком широк. Проявляй интеллектуальную любознательность.
                                Критически важные правила:
                                    Честность и прозрачность: Если ты чего-то не знаешь или не уверен в ответе, никогда не выдавай догадку за факт. Честно скажи: «На основании предоставленного документа я не могу дать точный ответ на этот вопрос».
                                    Безопасность: Не создавай вредоносный, неэтичный или опасный контент. Если запрос выходит за эти рамки, вежливо откажись, объяснив причину.
                                    Фокус на документе: Первичным источником информации для тебя всегда является документ пользователя. Твои общие знания — это вспомогательный инструмент для лучшего объяснения, а не замена анализу текста."""
            }
        print(prompt)
        response = await self.generate_response(
            prompt
        )
        return {
                "status": "success",
                "message": response['message'],
                "original_request": payload
            }

# Создаем экземпляр сервиса для dependency injection
orchestrate_processing = OrchestrationService()
logger.info("OrchestrationService создан и готов к работе")