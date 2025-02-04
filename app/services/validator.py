import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from langdetect import detect  # type: ignore
import re
from app.core.logging import setup_logging
from app.models.schemas import ValidationResult, URLRequest


logger = setup_logging(__name__)

class DocumentationValidator:
    def __init__(self) -> None:
        pass

    async def validate_url(self, request: URLRequest) -> ValidationResult:
        url = request.url
        result: ValidationResult = {
            "is_documentation": False,
            "confidence_score": 0,
            "checks_passed": {
                "url_pattern": {},
                "http_check": {},
                "keywords": {},
                "structure": {},
                "metadata": False,
                "language": False,
            },
            "threshold": 8,
        }

        try:
            async with httpx.AsyncClient() as client:
                result = self._check_url_patterns(url, result)

                response = await self._get_and_validate_response(client, url)
                result = self._check_https_response(response, result)

                soup = BeautifulSoup(response.text, "html.parser")
                result = self._analyze_content(soup, result)

                result["is_documentation"] = (
                    result["confidence_score"] >= result["threshold"]
                )
                return ValidationResult(**result)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error validating {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error validating {url}: {str(e)}")
            raise

    async def _get_and_validate_response(
        self, client: httpx.AsyncClient, url: str
    ) -> httpx.Response:
        response = await client.get(url, follow_redirects=True, timeout=10)
        response.raise_for_status()
        return response

    def _check_url_patterns(
        self, url: str, result: ValidationResult
    ) -> ValidationResult:
        parsed_url = urlparse(url)
        url_checks = {
            "docs_in_domain": any(
                s in parsed_url.netloc for s in ["docs.", "developer."]
            ),
            "docs_in_path": any(
                s in parsed_url.path.lower() for s in ["docs", "documentation", "api"]
            ),
            "known_platform": any(
                d in parsed_url.netloc for d in ["readthedocs.io", "gitbook.io"]
            ),
        }
        result["checks_passed"]["url_pattern"] = url_checks
        result["confidence_score"] += sum(url_checks.values()) * 2
        return result

    def _check_https_response(
        self, response: httpx.Response, result: ValidationResult
    ) -> ValidationResult:
        content_type = response.headers.get("Content-Type", "")
        html_check = {
            "status_ok": response.status_code == 200,
            "html_content": "text/html" in content_type,
        }
        result["checks_passed"]["http_check"] = html_check
        result["confidence_score"] += sum(html_check.values()) * 3
        return result

    def _analyze_content(
        self, soup: BeautifulSoup, result: ValidationResult
    ) -> ValidationResult:
        text_content = soup.get_text().lower()

        keywords = {
            "tutorial": bool(re.search(r"\btutorial\b", text_content)),
            "api": bool(re.search(r"\bapi\b", text_content)),
            "getting started": bool(re.search(r"getting started", text_content)),
            "code_blocks": len(soup.find_all(["pre", "code"])) > 3,
        }
        result["checks_passed"]["keywords"] = keywords
        result["confidence_score"] += sum(keywords.values()) * 1

        structure_checks = {
            "has_sidebar": bool(
                soup.find(
                    [
                        "nav",
                        "aside",
                    ]
                )
            ),
            "has_toc": bool(
                soup.find(id="toc") or soup.find(class_="table-of-contents")
            ),
            "search_bar": bool(
                soup.find("input", {"placeholder": re.compile(r"search", re.I)})
            ),
        }

        result["checks_passed"]["structure"] = structure_checks
        result["confidence_score"] += sum(structure_checks.values()) * 2

        meta_description = soup.find("meta", attrs={"name": "description"})
        meta_check = meta_description and any(
            s in meta_description.get("content", "").lower()  # type: ignore
            for s in ["documentation", "technical guide", "api"]
        )

        result["checks_passed"]["metadata"] = meta_check  # type: ignore
        if meta_check:
            result["confidence_score"] += 3

        main_text = " ".join([p.get_text() for p in soup.find_all(["p", "li"])][:5])
        if main_text:
            result["checks_passed"]["language"] = detect(main_text) == "en"

        return result
