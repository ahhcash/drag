from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from langchain_postgres import PGVector
from app.models.api import DocumentChunk, IngestionStatus
from app.core.logging import setup_logging
from app.core.config import get_settings
from app.models.api import (
    DocumentationSetRead,
    DocumentationSetCreate,
)
from app.models.db import DocumentationSet, IngestionTask
import uuid

logger = setup_logging(__name__)

BATCH_SIZE = 10000


class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = OpenAIEmbeddings()

        self.conn_string = self.settings.supabase_postgres_url

        self.async_conn_string = self.settings.async_postgres_url

        self.engine = create_async_engine(
            self.conn_string,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def create_doc_set(
        self, doc_set_create: DocumentationSetCreate
    ) -> DocumentationSetRead:
        """Create a new documentation set and return it"""
        try:
            # Convert API model to DB model
            db_doc_set = DocumentationSet(
                name=doc_set_create.name, root_url=doc_set_create.root_url
            )

            async with AsyncSession(self.engine) as session:
                session.add(db_doc_set)
                await session.commit()
                await session.refresh(db_doc_set)

                response = DocumentationSetRead.model_validate(db_doc_set.model_dump())
                logger.info(f"Created new doc set with ID: {response.id}")
                return response

        except IntegrityError:
            raise ValueError(
                f"documentation set with name {doc_set_create.name} exists!"
            )
        except Exception as e:
            logger.error(f"Failed to create doc set: {str(e)}")
            raise

    async def update_chunk_count(self, doc_set_id: uuid.UUID, chunk_count: int) -> None:
        try:
            async with AsyncSession(self.engine) as session:
                # Find the doc set
                statement = select(DocumentationSet).where(
                    DocumentationSet.id == doc_set_id
                )
                result = await session.execute(statement)
                doc_set = result.scalar_one_or_none()

                if not doc_set:
                    raise ValueError(f"Doc set {doc_set_id} not found")

                # Update the count
                doc_set.total_chunks = chunk_count
                await session.commit()

                logger.info(
                    f"Updated chunk count for doc set {doc_set_id}: {chunk_count}"
                )

        except Exception as e:
            logger.error(f"Failed to update chunk count: {str(e)}")
            raise

    async def get_doc_set(
        self, doc_set_id: uuid.UUID
    ) -> Optional[DocumentationSetRead]:
        try:
            async with AsyncSession(self.engine) as session:
                statement = select(DocumentationSet).where(
                    DocumentationSet.id == doc_set_id
                )
                result = await session.execute(statement)
                doc_set = result.scalar_one_or_none()

                if doc_set:
                    return DocumentationSetRead.model_validate(doc_set)
                return None

        except Exception as e:
            logger.error(f"Failed to get doc set: {str(e)}")
            raise

    async def update_ingestion_task_status(
        self,
        task_id: uuid.UUID,
        status: IngestionStatus,
        error_message: str | None = None,
    ) -> None:
        async with AsyncSession(self.engine) as session:
            task = await session.get(IngestionTask, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.status = status.value
            if error_message:
                task.error_message = error_message
            await session.commit()

    async def get_ingestion_task(self, task_id: uuid.UUID) -> IngestionTask:
        async with AsyncSession(self.engine) as session:
            ingestion_task: Optional[IngestionTask] = await session.get(
                IngestionTask, task_id
            )
            if not ingestion_task:
                raise ValueError(f"Task {task_id} not found")
            return ingestion_task

    async def store_chunks(
        self, chunks: List[DocumentChunk], doc_set_id: uuid.UUID, name: str
    ) -> None:
        try:
            collection_name = f"{doc_set_id}_{name}"

            texts = [chunk.content for chunk in chunks]
            metadata = [
                {
                    "url": chunk.url,
                    "title": chunk.title,
                    "parent_headings": chunk.parent_headings,
                    "chunk_hash": chunk.chunk_hash,
                    "id": str(uuid.uuid4()),
                }
                for chunk in chunks
            ]

            embedding_store = PGVector(
                collection_name=collection_name,
                connection=self.engine,
                embeddings=self.embeddings,
                pre_delete_collection=True,
            )

            # Store the embeddings
            await embedding_store.aadd_texts(
                texts=texts,
                metadatas=metadata,
            )

            # Now store the langchain collection ID in our documentation_sets table
            async with AsyncSession(self.engine) as session:
                # First find the langchain collection using SQLModel
                from sqlalchemy import text

                stmt = text(
                    "SELECT uuid FROM langchain_pg_collection WHERE name = :name"
                )
                result = await session.execute(stmt, {"name": collection_name})
                row = result.fetchone()

                if row and row[0]:
                    # Get the doc set
                    statement = select(DocumentationSet).where(
                        DocumentationSet.id == doc_set_id
                    )
                    result = await session.execute(statement)
                    doc_set = result.scalar_one_or_none()

                    if doc_set:
                        # Update using the ORM
                        doc_set.langchain_collection_id = row[0]
                        doc_set.langchain_collection_name = collection_name
                        await session.commit()

            await self.update_chunk_count(doc_set_id, len(chunks))
            logger.info(f"Stored {len(chunks)} chunks for doc set {doc_set_id}")

        except Exception as e:
            logger.error(f"Failed to store vectors: {str(e)}")
            raise

    async def similarity_search(
        self, query: str, doc_set_id: uuid.UUID, k: int = 4
    ) -> List[DocumentChunk]:
        try:
            doc_set = await self.get_doc_set(doc_set_id)
            if not doc_set:
                raise ValueError(f"Doc set {doc_set_id} not found")

            if not doc_set.langchain_collection_name:
                raise ValueError(
                    f"Doc set {doc_set_id} has no associated langchain collection"
                )

            # Use the stored collection name from our database
            store = PGVector(
                collection_name=doc_set.langchain_collection_name,
                embeddings=self.embeddings,
                connection=self.conn_string,
            )

            # Use similarity search
            docs = store.similarity_search(query, k=k)

            # Convert to our DocumentChunk model
            return [
                DocumentChunk(
                    content=doc.page_content,
                    url=doc.metadata["url"],
                    title=doc.metadata["title"],
                    parent_headings=doc.metadata["parent_headings"],
                    chunk_hash=doc.metadata["chunk_hash"],
                )
                for doc in docs
            ]

        except Exception as e:
            logger.error(f"Failed to search vectors: {str(e)}")
            raise
