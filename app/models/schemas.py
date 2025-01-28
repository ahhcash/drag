from pydantic import BaseModel
from typing import List

class URLRequest(BaseModel):
    url: str

class ValidationResult(BaseModel):
    is_documentation: bool
    confidence_score: int
    checks_passed: dict
    threshold: int = 8

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
