from fastapi import APIRouter, Depends, Request
from api.models.request import GenerationRequest

def get_bot_from_request(request: Request):
    return request.app.state.yandex_bot

router = APIRouter()


@router.post("/generate")
async def process_request(request: GenerationRequest, gpt = Depends(get_bot_from_request)):
    answer = gpt.ask_gpt(request.user_prompt, request.system_prompt)
    return {"message": answer}