from fastapi import APIRouter
from app.models.api import HealthCheckResult
from app.core.logging import setup_logging


router = APIRouter()
logger = setup_logging(__name__)


@router.get("/", response_model=HealthCheckResult)
async def health_check():
    logger.info("Health check endpoint called")
    return HealthCheckResult(healthy=True)
