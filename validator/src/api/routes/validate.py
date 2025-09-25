import re
from fastapi import APIRouter

from api.models.request import ValidationRequest
from clients.validator_client import ModeratorClient

from log.logger import logger


router = APIRouter()

patterns = {
    "prompt_injection": [
        r"(?i)(игнорируй|забудь|смени|измени).*(инструкц|правил|систем|предыдущ)",
        r"(?i)(выполни|сделай|напиши).*(как|вместо|в роли).*(пользователь|систем|админ)",
        r"(?i)(ignore|forget|override|system).*(prompt|instructions|previous)",
    ],
    "leak_sensitive_data": [
        r"(?i)(парол|креденш|токен|api[_-]?key|секрет|auth|ключ|access[_-]?key)",
        r"(?i)(личн|персональн|конфиденц|паспорт|банковск|карт|счет|password|credit|card)",
    ],
    "code_execution": [
        r"(?i)(exec|eval|system|os\.|subprocess|компилир|выполни.*код|запусти.*програм)",
        r"(`{3}|\b(?:import|fork|execve|socket|syscall)\b)",
    ],
    "bypass_filters": [
        r"(?i)(обойди|обход|bypass|обмани|фильтр|модерац)",
        r"(\bне\s+проверяй\b|\bignore\s+filter\b)",
        r"(\\x[0-9a-fA-F]|урл|кодировк|base64)",
    ],
}

def check_fraud(text):
    alerts = []
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text):
                alerts.append((category, pattern))
                break
    return alerts

@router.post("/validate")
async def process_request(request: ValidationRequest):
    alerts = check_fraud(request.text)
    
    for alert in alerts:
        logger.warning(f"\n\n{request.user_id} Попытался взломать модель: {alert[0]}\nСообщение: {request.text}\n\n")
        return {"is_valid": False}
    print(request)
    response = await ModeratorClient().moderate(request.model_dump())
    print(response)
    if not response.get("is_valid", False):
        return {"is_valid": False}
    
    return {"is_valid": True}