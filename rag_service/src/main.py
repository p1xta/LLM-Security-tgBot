from fastapi import FastAPI
import uvicorn

from .api.routes import main_router


def create_app() -> FastAPI:
    app = FastAPI(title="Yandex GPT Service", version="1.0.0")
    
    app.include_router(main_router)
    
    return app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8002)