from .moderate import router as validation_router
from .generate import router as generation_router

from fastapi import APIRouter
main_router = APIRouter()
main_router.include_router(validation_router, tags=["validation"])
main_router.include_router(generation_router, tags=["generation"])

__all__ = ["main_router"]