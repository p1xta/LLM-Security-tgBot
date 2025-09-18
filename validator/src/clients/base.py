import httpx
from typing import Dict, Any
from ..config.settings import get_settings

settings = get_settings()

class BaseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = settings.REQUEST_TIMEOUT
    
    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()