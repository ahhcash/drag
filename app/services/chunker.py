from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from app.models.api import DocPage, DocumentChunk
from typing import List


class DocumentationChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on
        )

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def chunk(self, doc_page: DocPage) -> List[DocumentChunk]:
        header_splits = self.header_splitter.split_text(doc_page.content)
        all_chunks = []
        for split in header_splits:
            headers = []
            for level in ["h1", "h2", "h3", "h4"]:
                if level in split.metadata and split.metadata[level]:
                    headers.append(split.metadata[level])

            chunks = self.splitter.split_text(split.page_content)

            for chunk in chunks:
                all_chunks.append(
                    DocumentChunk(
                        content=chunk,
                        url=doc_page.url,
                        title=doc_page.title,
                        parent_headings=headers,
                        chunk_hash=f"{hash(chunk)}-{doc_page.url}",
                    )
                )

        return all_chunks
