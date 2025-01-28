from pydantic import BaseModel
from typing import List, TypedDict, Dict


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
