import tempfile

from crawlee import EnqueueStrategy
from crawlee.crawlers import BeautifulSoupCrawler
from crawlee.crawlers._beautifulsoup import BeautifulSoupCrawlingContext
from urllib.parse import urlparse
from datetime import timedelta
import html2text
from langchain_community.document_loaders import UnstructuredHTMLLoader

from app.models.api import DocPage, CrawlRequest
from app.core.logging import setup_logging
from typing import List

logger = setup_logging(__name__)


class DocumentationCrawler:
    def __init__(self) -> None:
        self.collected_pages: List[DocPage] = []
        self.md_converter = html2text.HTML2Text()
        self.md_converter.ignore_links = False

    async def crawl(self, request: CrawlRequest) -> List[DocPage]:
        logger.info(f"starting crawl for {request.url}")
        self.collected_pages = []

        crawler = BeautifulSoupCrawler(
            max_requests_per_crawl=request.max_pages,
            request_handler_timeout=timedelta(seconds=30),
        )

        @crawler.router.default_handler
        async def handler(context: BeautifulSoupCrawlingContext) -> None:
            parsed_start = urlparse(request.url)
            parsed_current = urlparse(context.request.url)

            if parsed_current.netloc != parsed_start.netloc:
                context.log.info(f"skipping external domain: {context.request.url}")
                return

            page = await self._process_page(context)
            if page:
                self.collected_pages.append(page)
                await context.enqueue_links(strategy=EnqueueStrategy.SAME_DOMAIN)

        await crawler.run([request.url])
        return self.collected_pages

    async def _process_page(
        self, context: BeautifulSoupCrawlingContext
    ) -> DocPage | None:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html") as tmp:
                tmp.write(str(context.soup))
                tmp.flush()

                loader = UnstructuredHTMLLoader(tmp.name, mode="elements")
                elements = loader.load()

            content = "\n\n".join(str(element) for element in elements)

            title = (context.soup.title.string if context.soup.title else "Untitled") or "Untitled"

            headings = [h.get_text() for h in context.soup.find_all(["h1", "h2", "h3"])]

            return DocPage(
                url=context.request.url, title=title, content=content, headings=headings
            )
        except Exception as e:
            logger.error(f"failed to process page {context.request.url}: {str(e)}")
            return None
