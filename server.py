from fastapi import FastAPI
from app.core.logging import setup_logging, LoggingMiddleware
from app.api.routes import health, docs

logger = setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(title="drag - docs rag chatbot")

    app.add_middleware(LoggingMiddleware)

    app.include_router(health.router, tags=["health"])
    app.include_router(docs.router, prefix="/docs", tags=["documentation"])

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="localhost", port=8000, reload=True)
