from .base import BaseClient
from ..config.settings import get_settings

settings = get_settings()

class LLMClient(BaseClient):
    def __init__(self):
        super().__init__(settings.LLM_URL)
    
    async def generate(self, payload: dict) -> dict:
        return await self._post("/generate", payload)