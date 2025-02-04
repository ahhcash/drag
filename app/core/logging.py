import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time


def setup_logging(name: str):
    log = logging.getLogger(name)

    if log.hasHandlers():
        return log

    log.setLevel(logging.INFO)
    log.propagate = True

    return log


logger = setup_logging(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        logger.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Duration: {duration:.2f}s"
            )
            return response
        except Exception as e:
            logger.error(
                f"Request failed: {request.method} {request.url.path} - Error: {str(e)}"
            )
            raise
