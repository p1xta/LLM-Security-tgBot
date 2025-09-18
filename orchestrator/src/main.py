from fastapi import FastAPI
from .api.routes import main_router as api_router
from .config.settings import get_settings
#from .utils.logging import setup_logging

def create_app() -> FastAPI:
    settings = get_settings()
    #setup_logging(level=settings.LOG_LEVEL)
    
    app = FastAPI(
        title="Orchestrator Service",
        version="1.0.0",
        debug=settings.DEBUG
    )
    
    app.include_router(api_router)
    
    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)