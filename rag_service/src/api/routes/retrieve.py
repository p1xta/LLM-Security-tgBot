from fastapi import APIRouter, Depends, HTTPException
from ...clients.faiss_bridge import FAISSbridge
from ...clients.s3_bridge import S3Bridge
from ...api.models.request import RAGRequest
from ...api.models.response import RAGResponse
from ...exceptions.specific import ValidationFailedError, ServiceUnavailableError

retrieve_router = APIRouter()

@retrieve_router.post("/retrieve", response_model=RAGRequest)
async def retrieve_context(
    request: RAGRequest,
    faiss_service: FAISSbridge = Depends(),
    s3_service: S3Bridge = Depends(),
):
    try:
        docs = s3_service.download_from_s3(req.bucket, req.folder)
        if not docs:
            return RAGResponse(
                message="Документы не найдены",
                original_request=request.model_dump(),
                chunks=[]
            )
        
        faiss_service.store_doc_vectors(docs)
        retrieved = faiss_service.find_relevant_data(request.query)
        return RAGResponse(**retrieved)
    except ValidationFailedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")