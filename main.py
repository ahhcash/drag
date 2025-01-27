from crawlee import EnqueueStrategy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from crawlee.crawlers import BeautifulSoupCrawler, PlaywrightCrawler, PlaywrightCrawlingContext
from urllib.parse import urlparse
from langdetect import detect
import re
import logger as logs
from typing import List

logger = logs.setup_logging()

app = FastAPI()

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


@app.get("/", response_model = HealthCheckResult)
async def health_check():
    return HealthCheckResult(healthy=True)


@app.post("/validate-docs", response_model=ValidationResult)
async def validate_documentation(request: URLRequest):
    url = request.url
    result  = {"is_documentation": False, "confidence_score": 0, "checks_passed": {}, "threshold": 8}

    try:
        # 1. URL Pattern Check
        parsed_url = urlparse(url)
        logger.info(f"Parsed URL: {parsed_url}")
        url_checks = {
            "docs_in_domain": any(s in parsed_url.netloc for s in ["docs.", "developer."]),
            "docs_in_path": any(s in parsed_url.path.lower() for s in ["docs", "documentation", "api"]),
            "known_platform": any(d in parsed_url.netloc for d in ["readthedocs.io", "gitbook.io"])
        }
        result["checks_passed"]["url_pattern"] = url_checks
        result["confidence_score"] += sum(url_checks.values()) * 2


        # 2. HTTP Response Check
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get('Content-Type', '')
        html_check = {
            "status_ok": response.status_code == 200,
            "html_content": "text/html" in content_type
        }
        result["checks_passed"]["http_check"] = html_check
        result["confidence_score"] += sum(html_check.values()) * 3


        # 3. Content Analysis
        soup = BeautifulSoup(response.text, 'html.parser')
        text_content = soup.get_text().lower()

        # Keyword matching
        keywords = {
            "tutorial": bool(re.search(r'\btutorial\b', text_content)),
            "api": bool(re.search(r'\bapi\b', text_content)),
            "getting started": bool(re.search(r'getting started', text_content)),
            "code_blocks": len(soup.find_all(['pre', 'code'])) > 3
        }
        result["checks_passed"]["keywords"] = keywords
        result["confidence_score"] += sum(keywords.values()) * 1


        structure_checks = {
            "has_sidebar": bool(soup.find(['nav', 'aside',])), # type: ingore
            "has_toc": bool(soup.find(id='toc') or soup.find(class_='table-of-contents')),
            "search_bar": bool(soup.find('input', {'placeholder': re.compile(r'search', re.I)}))
        }

        result["checks_passed"]["structure"] = structure_checks
        result["confidence_score"] += sum(structure_checks.values()) * 2

        meta_description = soup.find('meta', attrs={'name': 'description'})
        meta_check = meta_description and any(s in meta_description.get('content', '').lower() for s in ["documentation", "technical guide", "api"])

        logger.info(meta_check)

        result["checks_passed"]["metadata"] = meta_check
        if meta_check:
            result["confidence_score"] += 3
        logger.info(f"Partial result 5: {result}")

        # 6. Language Check (optional)
        main_text = ' '.join([p.get_text() for p in soup.find_all(['p', 'li'])][:5])
        if main_text:
            result["checks_passed"]["language"] = detect(main_text) == 'en'

        # Final determination
        result["is_documentation"] = result["confidence_score"] >= result["threshold"]
        logger.info(f"Partial result 6: {result}")

        return ValidationResult(**result)

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"URL fetch failed: {str(e)}")
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


async def is_doc_page(html: str, url: str) -> bool:
    # quick check if this page seems like documentation
    soup = BeautifulSoup(html, 'html.parser')

    # check url patterns
    doc_patterns = ['/docs/', '/api/', '/guide/', '/reference/']
    if any(pattern in url.lower() for pattern in doc_patterns):
        return True

    # look for documentation markers
    headings = soup.find_all(['h1', 'h2', 'h3'])
    doc_keywords = ['documentation', 'guide', 'api reference', 'getting started']
    if any(kw in h.get_text().lower() for h in headings for kw in doc_keywords):
        return True

    # check for code blocks
    if len(soup.find_all(['pre', 'code'])) > 2:
        return True

    return False

@app.post("/crawl-docs")
async def crawl_docs(request: CrawlRequest):
    crawler = PlaywrightCrawler(
        max_requests_per_crawl=request.max_pages,
        headless = True,
    )

    collected_pages: List[DocPage] = []

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        # only process pages from same domain
        if not context.request.url.startswith(request.url):
            return

        context.log.info(f'Checking {context.request.url}')

        # get page content
        html = await context.page.content()

        # check if it's actually documentation
        if not await is_doc_page(html, context.request.url):
            return

        # extract useful content
        soup = BeautifulSoup(html, 'html.parser')

        # get main content area if possible
        main_tag = soup.find('main') or soup.find('article') or soup.find('body') or soup

        if isinstance(main_tag, str):
            main_tag = BeautifulSoup(main_tag, 'html.parser')

        # clean up content
        for tag in main_tag.find_all(['script', 'style', 'nav', 'footer']):
            tag.decompose()

        # extract headings for structure
        headings = [h.get_text().strip() for h in main_tag.find_all(['h1', 'h2', 'h3'])]

        content = main_tag.get_text(separator=' ', strip=True)

                # remove excessive whitespace and newlines
        content = ' '.join(content.split())

        try:
            page = DocPage(
                url=context.request.url,
                title=await context.page.title() or "Untitled",
                content=content,
                headings=headings
            )
            collected_pages.append(page)
            context.log.info(f'Successfully processed {context.request.url}')
        except Exception as e:
            context.log.error(f'Failed to process {context.request.url}: {str(e)}')

        await context.enqueue_links(strategy = EnqueueStrategy.SAME_DOMAIN)

    # start the crawl
    await crawler.run([request.url])

    return collected_pages

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
