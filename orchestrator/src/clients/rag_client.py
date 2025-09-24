from .base import BaseClient
from config.settings import get_settings
import httpx

settings = get_settings()

class RAGClient(BaseClient):
    def __init__(self):
        super().__init__(settings.RAG_URL)
    
    async def retrieve(self, payload: dict) -> dict:
        print(payload)
        return await self._post("/retrieve", payload)

    async def upload(self, bucket: str, user_id: str, file):
        async with httpx.AsyncClient() as client:
            files = {"file": (file.filename, file.file, file.content_type)}
            data = {"bucket": bucket, "user_id": user_id}
            response = await client.post(
                f"{self.base_url}/upload",
                data=data,
                files=files,
                timeout=60
            )
            response.raise_for_status()
            return response.json()