from .base import BaseClient
from ..config.settings import get_settings

settings = get_settings()

class ValidatorClient(BaseClient):
    def __init__(self):
        super().__init__(settings.VALIDATOR_URL)
    
    async def validate(self, payload: dict) -> dict:
        return await self._post("/validate", payload)