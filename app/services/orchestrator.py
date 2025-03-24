import asyncio
from typing import List
from uuid import UUID

from prefect import task, flow
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.logging import setup_logging
from app.models.api import (
    CrawlRequest,
    DocPage,
    DocumentChunk,
    DocumentationSetCreate,
    DocumentationSetRead,
    IngestionStatus,
)
from app.models.db import IngestionTask
from app.services.chunker import DocumentationChunker
from app.services.crawler import DocumentationCrawler
from app.services.store import VectorStore
from app.services.validator import DocumentationValidator

validator = DocumentationValidator()
crawler = DocumentationCrawler()
chunker = DocumentationChunker()
store = VectorStore()
logger = setup_logging(__name__)


# @task(
#     retries=3,
#     cache_key_fn=task_input_hash,
#     retry_delay_seconds=30,
#     cache_expiration=timedelta(hours=24),
# )
# async def validate(url: str) -> bool:
#     url_req = URLRequest(url=url)
#     result = await validator.validate_url(url_req)
#     if not result["is_documentation"]:
#         raise ValueError(f"URL {url} does not appear to be documentation!")
#     return True


@task(retries=2)
async def crawl(url: str, max_pages: int = 100) -> List[DocPage]:
    return await crawler.crawl(CrawlRequest(url=url, max_pages=max_pages))


@task
async def chunk_doc(page: DocPage) -> List[DocumentChunk]:
    return chunker.chunk(page)


@task
async def merge_chunks(chunk_lists: List[List[DocumentChunk]]) -> List[DocumentChunk]:
    return [chunk for chunks in chunk_lists for chunk in chunks]


@task
async def chunk_docs(pages: List[DocPage]) -> List[DocumentChunk]:
    chunk_lists = await asyncio.gather(*[chunk_doc(page) for page in pages])
    return await merge_chunks(chunk_lists)


@task(retries=2)
async def store_doc_chunks(
    chunks: List[DocumentChunk], doc_set_id: UUID, name: str
) -> int:
    await store.store_chunks(chunks, doc_set_id, name)
    return len(chunks)


@task
async def create_doc_set(url: str, name: str) -> DocumentationSetRead:
    doc_set = DocumentationSetCreate(name=name, root_url=url)
    return await store.create_doc_set(doc_set)


@flow(name="ingest docs")
async def ingest(task_id: UUID, url: str, name: str, max_pages: int = 100) -> None:
    try:
        await store.update_ingestion_task_status(task_id, IngestionStatus.RUNNING)
        # await validate(url)
        doc_set = await create_doc_set(url, name)
        logger.info(f"created documentation set with ID: {doc_set.id}")

        async with AsyncSession(store.engine) as session:
            ingestion_task = await session.get(IngestionTask, task_id)
            assert ingestion_task, "could not fetch ingestion task from DB!"
            ingestion_task.documentation_set_id = doc_set.id
            await session.commit()

        pages = await crawl(url, max_pages)
        chunks = await chunk_docs(pages)
        stored = await store_doc_chunks(chunks, doc_set.id, name)
        logger.info(f"stored {stored} document chunks")

        await store.update_ingestion_task_status(task_id, IngestionStatus.COMPLETED)

    except Exception as e:
        logger.error(f"ingestion failed: {str(e)}")
        await store.update_ingestion_task_status(
            task_id, IngestionStatus.FAILED, str(e)
        )
        raise
