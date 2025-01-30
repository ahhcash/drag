from app.services.store import VectorStore
import asyncio
from datetime import timedelta
from prefect import task, flow
from prefect.tasks import task_input_hash

from app.models.schemas import CrawlRequest, DocPage, DocumentChunk, DocumentationSetCreate, DocumentationSetRead, URLRequest
from app.services.crawler import DocumentationCrawler
from app.services.validator import DocumentationValidator

from typing import List, Tuple
from app.services.chunker import DocumentationChunker
from app.models.schemas import DocumentationSet
from app.core.logging import logger
from uuid import UUID

validator = DocumentationValidator()
crawler = DocumentationCrawler()
chunker = DocumentationChunker()
store = VectorStore()


@task(
    retries=3,
    cache_key_fn=task_input_hash,
    retry_delay_seconds=30,
    cache_expiration=timedelta(hours=24),
)
async def validate(url: str) -> bool:
    url_req = URLRequest(url=url)
    result = await validator.validate_url(url_req)
    if not result["is_documentation"]:
        raise ValueError(f"URL {url} does not appear to be documentation!")
    return True


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
async def store_doc_chunks(chunks: List[DocumentChunk], doc_set_id: UUID) -> int:
    await store.store_chunks(chunks, doc_set_id)
    return len(chunks)


@task
async def create_doc_set(url: str, name: str) -> DocumentationSetRead:
    doc_set = DocumentationSetCreate(name=name, root_url=url)
    return await store.create_doc_set(doc_set)


@flow(name="ingest docs")
async def ingest(url: str, name: str, max_pages: int = 100) -> Tuple[UUID, int]:
    await validate(url)
    doc_set = await create_doc_set(url, name)
    logger.info(f"created documentation set with ID: {doc_set.id}")

    pages = await crawl(url, max_pages)
    logger.info(f"crawled {len(pages)} of documentation")

    chunks = await chunk_docs(pages)
    logger.info(f"created a set of {len(chunks)} chunks from all pages")

    stored = await store_doc_chunks(chunks, doc_set.id)
    logger.info(f"stored {stored} chunks in PGvector")

    logger.info(f"Ingested {stored} chunks in PGVector for doc_set {doc_set.id}")
    return doc_set.id, stored
