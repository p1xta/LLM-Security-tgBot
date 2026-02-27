from .process import router as process_router

from fastapi import APIRouter
main_router = APIRouter()
main_router.include_router(process_router, tags=["process"])

__all__ = ["main_router"]