import logging
from pathlib import Path
from datetime import datetime
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time

def setup_logging():
    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler - new file each day
            logging.FileHandler(
                f'logs/app_{datetime.now().strftime("%Y-%m-%d")}.log'
            )
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # Log the incoming request
        logger.info(f"Request started: {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # Calculate request duration
            duration = time.time() - start_time

            # Log the completed request
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
