from enum import Enum

from pydantic import BaseModel
from typing import List, TypedDict, Dict
from datetime import datetime
import uuid


class IngestionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionTaskRead(BaseModel):
    id: uuid.UUID
    documentation_set_id: uuid.UUID | None
    status: IngestionStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    url: str

    class Config:
        from_attributes = True


class DocumentationSetRead(BaseModel):
    id: uuid.UUID
    name: str
    root_url: str
    total_chunks: int
    created_at: datetime
    updated_at: datetime
    langchain_collection_name: str | None

    class Config:
        from_attributes = True


class DocumentationSetCreate(BaseModel):
    name: str
    root_url: str


class URLRequest(BaseModel):
    url: str


class ValidationChecks(TypedDict):
    url_pattern: Dict[str, bool]
    http_check: Dict[str, bool]
    keywords: Dict[str, bool]
    structure: Dict[str, bool]
    metadata: bool
    language: bool


class ValidationResult(TypedDict):
    is_documentation: bool
    confidence_score: int
    checks_passed: ValidationChecks
    threshold: int


class HealthCheckResult(BaseModel):
    healthy: bool


class DocPage(BaseModel):
    url: str
    title: str
    content: str
    headings: List[str]


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 100


class DocumentChunk(BaseModel):
    content: str
    url: str
    title: str
    parent_headings: List[str]
    chunk_hash: str  # unique ID for deduping


class IngestRequest(BaseModel):
    url: str
    name: str  # maybe user facing name idk
    max_pages: int = 100


class DocIdentifier(BaseModel):
    id_or_name: str

    @property
    def is_valid_uuid(self) -> bool:
        try:
            _ = uuid.UUID(self.id_or_name)
            return True
        except ValueError:
            return False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    identifier: DocIdentifier
    message: str
    chat_history: List[ChatMessage] = []
