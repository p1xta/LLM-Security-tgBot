from .base import BaseClient
from config.settings import get_settings

settings = get_settings()

class RAGClient(BaseClient):
    def __init__(self):
        super().__init__(settings.RAG_URL)
    
    async def retrieve(self, payload: dict) -> dict:
        return await self._post("/retrieve", payload)
    
    async def upload(self, payload: dict) -> dict:
        return await self._post('/upload', payload)