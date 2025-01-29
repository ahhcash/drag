from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.pgvector import PGVector
from app.models.schemas import DocumentChunk
from app.core.logging import logger
from app.core.config import get_settings
import psycopg
from app.models.schemas import DocumentationSet


class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = OpenAIEmbeddings()

        self.connection_string = self.settings.supabase_postgres_url

        self.collection_name = "documentation_chunks"

    def _get_conn(self):
        return psycopg.connect(self.connection_string)

    async def create_doc_set(self, doc_set: DocumentationSet) -> str:
            try:
                with self._get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO documentation_sets (id, name, root_url)
                            VALUES (%s, %s, %s)
                            RETURNING id
                            """,
                            (doc_set.id, doc_set.name, doc_set.root_url)
                        )
                        assert cur.fetchone()
                        doc_set_id = cur.fetchone()[0] # type: ignore
                        conn.commit()
                        logger.info(f"Created new doc set with ID: {doc_set_id}")
                        return str(doc_set_id)
            except Exception as e:
                logger.error(f"Failed to create doc set: {str(e)}")
                raise

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
