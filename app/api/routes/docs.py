from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    IngestRequest,
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
from app.services.orchestrator import ingest

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


@router.post("/ingest")
async def ingest_docs(request: IngestRequest):
    try:
        doc_set_id, num_chunks = await ingest(
            url=request.url, name=request.name, max_pages=request.max_pages
        )
        return {
            "status": "success",
            "doc_set_id": doc_set_id,
            "chunks_stored": num_chunks,
            "message": f"successfully ingested {num_chunks} chunks from {request.url}",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ingestion failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="failed to ingest documentation, check logs for details",
        )
