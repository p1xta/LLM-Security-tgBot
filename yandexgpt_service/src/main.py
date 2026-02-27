import os
from fastapi import FastAPI
from api.routes import main_router as api_router
from config.settings import get_settings
from contextlib import asynccontextmanager
from utils.yandex_gpt import YandexGPTBot

from log.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    # создаём один экземпляр при запуске
    bot = YandexGPTBot()
    try:
        # опционально проверить токен сразу
        bot.get_iam_token()
        logger.info("Yandex бот инициализарован и токен получен.")
    except Exception:
        print("Ошибка при инициализации Yandex бота - продолжаем в любом случае.")
    app.state.yandex_bot = bot

    yield

    # опционально: чистка
    if hasattr(app.state, "yandex_bot"):
        del app.state.yandex_bot

def create_app() -> FastAPI:
    settings = get_settings()
    #setup_logging(level=settings.LOG_LEVEL)
    
    app = FastAPI(
        title="YandexGPT Service",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan
    )
    
    app.include_router(api_router)
    
    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ['PORT']))