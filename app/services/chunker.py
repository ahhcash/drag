from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
)

from app.core.logging import setup_logging
from app.models.api import DocPage, DocumentChunk
from typing import List

logger = setup_logging(__name__)

class DocumentationChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, doc_page: DocPage) -> List[DocumentChunk]:
        logger.info(f"doc page: {doc_page}")
        chunks = self.splitter.split_text(doc_page.content)

        return [
            DocumentChunk(
                content=chunk,
                url=doc_page.url,
                title=doc_page.title,
                parent_headings=doc_page.headings,
                chunk_hash=f"{hash(chunk)}-{doc_page.url}",
            )
            for chunk in chunks
        ]
