from typing import List
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores.pgvector import PGVector
from app.models.schemas import DocumentChunk
from app.core.logging import logger
import os


class VectorStore:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()

        self.connection_string = os.getenv(
            "SUPABASE_POSTGRES_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/vectors",
        )

        self.collection_name = "documentation_chunks"

    async def store_chunks(
        self, chunks: List[DocumentChunk], collection_prefix: str = ""
    ):
        """Store document chunks in pgvector with their embeddings."""
        try:
            collection = f"{collection_prefix}_{self.collection_name}"

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

            store = PGVector.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadata,
                collection_name=collection,
                connection_string=self.connection_string,
            )

            logger.info(f"Stored {len(chunks)} chunks in collection {collection}")
            return store

        except Exception as e:
            logger.error(f"Failed to store vectors: {str(e)}")
            raise

    async def similarity_search(
        self, query: str, collection_prefix: str = "", k: int = 4
    ) -> List[DocumentChunk]:
        """Search for similar chunks using vector similarity."""
        try:
            collection = f"{collection_prefix}_{self.collection_name}"

            store = PGVector(
                collection_name=collection,
                connection_string=self.connection_string,
                embedding_function=self.embeddings,
            )

            docs = store.similarity_search(query, k=k)

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

    async def delete_collection(self, collection_prefix: str = ""):
        """Delete a collection and all its vectors."""
        try:
            collection = f"{collection_prefix}_{self.collection_name}"
            store = PGVector(
                collection_name=collection,
                connection_string=self.connection_string,
                embedding_function=self.embeddings,
            )
            store.delete_collection()
            logger.info(f"Deleted collection {collection}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            raise
