from fastapi import APIRouter

from .message import router as message_router


main_router = APIRouter()
main_router.include_router(message_router, tags=["message"])

__all__ = ["main_router"]