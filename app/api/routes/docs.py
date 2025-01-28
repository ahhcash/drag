from fastapi import APIRouter, HTTPException
from app.models.schemas import URLRequest, ValidationResult, DocPage, CrawlRequest
from app.services.validator import DocumentationValidator
from app.core.logging import logger
from app.services.crawler import DocumentationCrawler
from typing import List

router = APIRouter()
validator = DocumentationValidator()
crawler = DocumentationCrawler()


@router.post("/validate", response_model=ValidationResult)
async def validate_documentation(request: URLRequest):
    try:
        return await validator.validate_url(request)
    except Exception as e:
        logger.error(f"Error validating documentation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl", response_model=List[DocPage])
async def crawl_docs(request: CrawlRequest):
    try:
        return await crawler.crawl(request)
    except Exception as e:
        logger.error(f"crawl failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
