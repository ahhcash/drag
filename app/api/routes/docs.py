from asyncio import create_task
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.api import (
    IngestRequest,
    URLRequest,
    ValidationResult,
    DocPage,
    CrawlRequest,
    DocumentChunk,
    IngestionStatus,
    IngestionTaskRead,
)
from app.models.db import IngestionTask
from app.services.store import VectorStore
from app.services.validator import DocumentationValidator
from app.core.logging import setup_logging
from app.services.crawler import DocumentationCrawler
from app.services.chunker import DocumentationChunker
from typing import List
from app.services.orchestrator import ingest

router = APIRouter()
validator = DocumentationValidator()
crawler = DocumentationCrawler()
chunker = DocumentationChunker()
store = VectorStore()
logger = setup_logging(__name__)


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


@router.post("/ingest", response_model=IngestionTaskRead)
async def ingest_docs(request: IngestRequest):
    try:
        async with AsyncSession(store.engine) as session:
            ingestion_task = IngestionTask(status=IngestionStatus.PENDING.value,
                                           url=request.url)
            session.add(ingestion_task)
            await session.commit()
            await session.refresh(ingestion_task)

        logger.info(f"created task: {ingestion_task}")

        create_task(
            ingest(
                task_id=ingestion_task.id,
                url=request.url,
                name=request.name,
                max_pages=request.max_pages,
            )
        )

        logger.info("created asyncio task to trigger prefect flow")
        return ingestion_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ingestion failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="failed to ingest documentation, check logs for details",
        )


@router.get("/ingest/{task_id}", response_model=IngestionTaskRead)
async def get_ingestion_status(task_id: UUID):
    logger.info(f"fetching ingestion task status: {task_id}")
    try:
        task = await store.get_ingestion_task(task_id)
        return task
    except Exception as e:
        logger.error(f"failed to get task status: {str(e)}")
        raise HTTPException(status_code=500, detail="failed to get task status")
