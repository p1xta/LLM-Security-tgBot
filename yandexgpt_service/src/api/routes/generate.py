from fastapi import APIRouter
from ..models.request import GenerationRequest
from ...utils.yandex_gpt import YandexGPTBot
import json

gpt = YandexGPTBot()
router = APIRouter()


@router.post("/generate")
async def process_request(request: GenerationRequest):
    answer = gpt.ask_gpt(request.user_prompt, request.system_prompt)
    return {"message": answer}