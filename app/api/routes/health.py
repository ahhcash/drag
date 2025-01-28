from fastapi import APIRouter
from app.models.schemas import HealthCheckResult
from app.core.logging import logger

router = APIRouter()

@router.get("/", response_model=HealthCheckResult)
async def health_check():
    logger.info("Health check endpoint called")
    return HealthCheckResult(healthy=True)
