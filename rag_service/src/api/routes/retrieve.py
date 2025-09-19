from fastapi import APIRouter, Depends, HTTPException
from ...clients.faiss_bridge import FAISSbridge
from ...clients.s3_bridge import S3Bridge
from ...api.models.request import RAGRequest
from ...api.models.response import RAGResponse
from ...exceptions.specific import ValidationFailedError, ServiceUnavailableError
import os
from dotenv import load_dotenv

router = APIRouter()


load_dotenv()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX")

faiss_service = FAISSbridge()
s3_service = S3Bridge(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name='ru-central1'
)

@router.post("/retrieve", response_model=RAGResponse)
async def retrieve_context(
    request: RAGRequest,
):
    try:
        docs = s3_service.download_from_s3(request.bucket, request.folder)
        if not docs:
            return RAGResponse(
                message="Документы не найдены",
                original_request=request.model_dump(),
                chunks=[]
            )
        
        faiss_service.store_doc_vectors(docs)
        retrieved = faiss_service.find_relevant_data(request.query)
        return {
            "original_request": request.model_dump(),
            "chunks": [doc.page_content for doc in retrieved]
        }
    except ValidationFailedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")