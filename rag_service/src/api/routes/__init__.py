from .retrieve import router as retrieve_router

from fastapi import APIRouter
main_router = APIRouter()
main_router.include_router(retrieve_router, tags=["retrieve"])

__all__ = ["main_router"]