from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from services.orchestration import OrchestrationService
from api.models.request import ProcessRequest, RAGUploadRequest
from api.models.response import ProcessResponse
from clients.rag_client import RAGClient
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

@router.post("/upload")
async def upload(
    bucket: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        result = await RAGClient().upload(
            bucket=bucket,
            user_id=user_id,
            file=file,
        )
        
        return result

    except ValidationFailedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")