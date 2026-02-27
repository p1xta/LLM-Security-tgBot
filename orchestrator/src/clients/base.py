import httpx
from typing import Dict, Any
from config.settings import get_settings
from utils.retry import with_retry
from utils.get_iam_token import get_iam_token_on_YC_vm

settings = get_settings()

class BaseClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = settings.REQUEST_TIMEOUT
    
    @with_retry(max_attempts=3, delay=1)
    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            iam_token = await get_iam_token_on_YC_vm(client)
            response = await client.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={
                    "Authorization": f"Bearer {iam_token}",
                    "Content-Type": "application/json"
                    },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()