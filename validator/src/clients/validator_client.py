from .base import BaseClient
from config.settings import get_settings

settings = get_settings()

class ModeratorClient(BaseClient):
    def __init__(self):
        super().__init__(settings.MODERATOR_URL)
    
    async def moderate(self, payload: dict) -> dict:
        return await self._post("/moderate", payload)