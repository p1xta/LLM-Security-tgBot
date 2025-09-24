from .base import BaseClient
from config.settings import get_settings
import httpx
from utils.get_iam_token import get_iam_token_on_YC_vm

settings = get_settings()

class RAGClient(BaseClient):
    def __init__(self):
        super().__init__(settings.RAG_URL)
    
    async def retrieve(self, payload: dict) -> dict:
        print(payload)
        return await self._post("/retrieve", payload)

    async def upload(self, bucket: str, user_id: str, file):
        
        async with httpx.AsyncClient() as client:
            iam_token = await get_iam_token_on_YC_vm(client)
            files = {"file": (file.filename, file.file, file.content_type)}
            data = {"bucket": bucket, "user_id": user_id}
            response = await client.post(
                f"{self.base_url}/upload",
                headers={
                    "Authorization": f"Bearer {iam_token}"
                },
                data=data,
                files=files,
                timeout=60
            )
            response.raise_for_status()
            return response.json()