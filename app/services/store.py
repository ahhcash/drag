from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from langchain_postgres import PGVector
from app.models.schemas import DocumentChunk
from app.core.logging import setup_logging
from app.core.config import get_settings
from app.models.schemas import (
    DocumentationSet,
    DocumentationSetRead,
    DocumentationSetCreate,
)
import uuid

logger = setup_logging(__name__)


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

    async def store_chunks(
        self, chunks: List[DocumentChunk], doc_set_id: uuid.UUID, name: str
    ) -> None:
        try:
            collection = f"{doc_set_id}_{name}"

            texts = [chunk.content for chunk in chunks]
            metadata = [
                {
                    "url": chunk.url,
                    "title": chunk.title,
                    "parent_headings": chunk.parent_headings,
                    "chunk_hash": chunk.chunk_hash,
                }
                for chunk in chunks
            ]

            _ = await PGVector.afrom_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadata,
                collection_name=collection,
                connection=self.conn_string,
            )

            # Update the document set's chunk count
            await self.update_chunk_count(doc_set_id, len(chunks))
            logger.info(f"Stored {len(chunks)} chunks for doc set {doc_set_id}")

        except Exception as e:
            logger.error(f"Failed to store vectors: {str(e)}")
            raise

    async def similarity_search(
        self, query: str, doc_set_id: uuid.UUID, k: int = 4
    ) -> List[DocumentChunk]:
        """Search for similar chunks in a doc set"""
        try:
            doc_set = await self.get_doc_set(doc_set_id)
            if not doc_set:
                raise ValueError(f"Doc set {doc_set_id} not found")

            collection = f"{doc_set_id}_{doc_set.name}"

            store = PGVector(
                collection_name=collection,
                embeddings=self.embeddings,
                connection=self.conn_string,
            )

            # Use async version of similarity search
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
