from app.core.config import get_settings
from app.models.api import DocPage, CrawlRequest
from app.core.logging import setup_logging
from typing import List
from firecrawl import FirecrawlApp

logger = setup_logging(__name__)


class DocumentationCrawler:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.firecrawl = FirecrawlApp(api_key=self.settings.firecrawl_api_key)

    async def crawl(self, request: CrawlRequest) -> List[DocPage]:
        logger.info(f"starting crawl for {request.url}")
        try:
            params = {
                "limit": int(self.settings.firecrawl_max_pages),
                "scrapeOptions": {"formats": ["markdown", "html"]},
            }
            crawl_status = self.firecrawl.crawl_url(
                request.url, params=params, poll_interval=10
            )
            pages = []

            for item in crawl_status.get("data", []):
                content = item.get("markdown", "")
                url = item.get("metadata", {}).get("sourceURL", "")
                title = item.get("metadata", {}).get("title", "Untitled")

                headings = [title]

                pages.append(
                    DocPage(url=url, title=title, content=content, headings=headings)
                )

            logger.info(f"completed crawl for {request.url}, found {len(pages)} pages")
            return pages
        except Exception as e:
            logger.error(f"crawl failed: {e}")
            raise

    async def crawl_async(self, request: CrawlRequest) -> List[DocPage]:
        logger.info(f"starting async crawl for {request.url}")
        try:
            params = {
                "limit": int(self.settings.firecrawl_max_pages),
                "scrapeOptions": {"formats": ["markdown", "html"]},
            }

            crawl_status = self.firecrawl.async_crawl_url(
                url=request.url, params=params
            )
            logger.info(f"triggered async crawl with status {crawl_status}")

            job_id = crawl_status.get("id")
            logger.info(f"async crawl started for {request.url} with job ID {job_id}")
            return job_id
        except Exception as e:
            logger.error(f"async crawl failed due to {e}")
            raise

    async def check_crawl_status(self, job_id: str):
        logger.info(f"checking status of job: {job_id}")
        try:
            status = self.firecrawl.check_crawl_status(job_id)
            return status
        except Exception as e:
            logger.error(f"crawl status check failed due to {e}")
            raise

    async def get_crawl_results(self, job_id: str) -> List[DocPage]:
        try:
            status = self.firecrawl.check_crawl_status(job_id)

            if status.get("status") != "completed":
                raise ValueError(f"Crawl job {job_id} is not completed yet")

            # Similar processing as in the crawl method
            pages = []
            for item in status.get("data", []):
                content = item.get("markdown", "")
                url = item.get("metadata", {}).get("sourceURL", "")
                title = item.get("metadata", {}).get("title", "Untitled")
                headings = [title]

                pages.append(
                    DocPage(url=url, title=title, content=content, headings=headings)
                )

            return pages
        except Exception as e:
            logger.error(f"crawl result fetch failed: {e}")
            raise
