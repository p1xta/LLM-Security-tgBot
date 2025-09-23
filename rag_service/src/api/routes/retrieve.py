import os

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Request

from clients.faiss_bridge import FAISSbridge
from clients.s3_bridge import S3Bridge
from api.models.request import RAGRequest, RAGUploadRequest
from api.models.response import RAGResponse
from exceptions.specific import ValidationFailedError, ServiceUnavailableError
from utils.get_secrets import get_all_secrets_payload
from log.logger import logger
import tempfile
import shutil

router = APIRouter()

secrets_dict = get_all_secrets_payload()
S3_ENDPOINT = secrets_dict["S3_ENDPOINT"]
S3_ACCESS_KEY = secrets_dict["S3_ACCESS_KEY"]
S3_SECRET_KEY = secrets_dict["S3_SECRET_KEY"]

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
        print(request)
        docs = s3_service.download_from_s3(s3_bucket=request.bucket, s3_folder=request.user_id)
        if not docs:
            logger.info("Документы в хранилище не найдены.")
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
        logger.error(f"Ошибка при получении контекста: код 400. {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceUnavailableError as e:
        logger.error(f"Ошибка при получении контекста: код 503. {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка при получении контекста: код 500. {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")


@router.post("/upload")
async def upload(
    bucket: str = Form(...),
    user_id: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        with tempfile.NamedTemporaryFile() as tmp:
            content = await file.read()
            with open(tmp.name, "wb") as f:
                f.write(content)
            tmp_path = tmp.name
            s3_service.upload_to_s3(bucket, tmp_path, dest_file_path=f"{user_id}/{file.filename}")

        docs = s3_service.download_from_s3(bucket, f"{user_id}")
        faiss_service.store_doc_vectors(docs)

        return {
            "status":"success",
            "message":f"Файл {file.filename} успешно загружен и проиндексирован.",
            "original_request":{"bucket": bucket, "user_id": user_id, "file": file.filename},
        }

    except ValidationFailedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Internal server error {e}")