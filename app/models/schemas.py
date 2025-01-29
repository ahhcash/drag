from pydantic import BaseModel, Field
from typing import List, TypedDict, Dict
from datetime import datetime
import uuid


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


class DocumentationSet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    root_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    total_chunks: int = 0


class IngestRequest(BaseModel):
    url: str
    name: str  # maybe user facing name idk
    max_pages: int = 100


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    documentation_id: str
    message: str
    chat_history: List[ChatMessage] = []
