from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    URLRequest,
    ValidationResult,
    DocPage,
    CrawlRequest,
    DocumentChunk,
)
from app.services.validator import DocumentationValidator
from app.core.logging import logger
from app.services.crawler import DocumentationCrawler
from app.services.chunker import DocumentationChunker
from typing import List

router = APIRouter()
validator = DocumentationValidator()
crawler = DocumentationCrawler()
chunker = DocumentationChunker()


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


@router.post("/chunk", response_model=List[DocumentChunk])
async def chunk_docs(doc_pages: List[DocPage]):
    logger.info(f"chunking request received for {len(doc_pages)} documents")
    try:
        all_chunks = []
        for doc_page in doc_pages:
            chunks = chunker.chunk(doc_page)
            all_chunks.extend(chunks)
        return all_chunks
    except Exception as e:
        logger.error(f"chunking failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
