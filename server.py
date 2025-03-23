from fastapi import FastAPI
from app.core.logging import setup_logging, LoggingMiddleware
from app.api.routes import chat, health, docs

logger = setup_logging(__name__)


def create_app() -> FastAPI:
    fastapi_app = FastAPI(title="drag - docs rag chatbot")

    fastapi_app.add_middleware(LoggingMiddleware)

    fastapi_app.include_router(health.router, tags=["health"])
    fastapi_app.include_router(docs.router, prefix="/docs", tags=["documentation"])
    fastapi_app.include_router(chat.router, prefix="/chat", tags=["chat"])
    return fastapi_app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="localhost", port=8080, reload=True)
