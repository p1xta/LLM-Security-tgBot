from .validate import router as validation_router

from fastapi import APIRouter
main_router = APIRouter()
main_router.include_router(validation_router, tags=["validation"])

__all__ = ["main_router"]