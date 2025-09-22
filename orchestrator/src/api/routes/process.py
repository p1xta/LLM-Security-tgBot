from fastapi import APIRouter, Depends, HTTPException
from services.orchestration import OrchestrationService
from api.models.request import ProcessRequest
from api.models.response import ProcessResponse
from exceptions.specific import ValidationFailedError, ServiceUnavailableError

router = APIRouter()

@router.post("/process", response_model=ProcessResponse)
async def process_request(
    request: ProcessRequest,
    orchestration_service: OrchestrationService = Depends()
):
    try:
        req_dict = request.model_dump()
        result = await orchestration_service(req_dict)
        return ProcessResponse(**result)
    except ValidationFailedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")