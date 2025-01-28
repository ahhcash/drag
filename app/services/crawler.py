from crawlee import EnqueueStrategy
from crawlee.crawlers import BeautifulSoupCrawler
from crawlee.crawlers._beautifulsoup import BeautifulSoupCrawlingContext
from urllib.parse import urlparse
from datetime import timedelta
import html2text
from app.models.schemas import DocPage, CrawlRequest
from app.core.logging import logger
from typing import List

class DocumentationCrawler:
    def __init__(self):
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
                context.log.info(f'skipping external domain: {context.request.url}')
                return

            page = await self._process_page(context)
            if page:
                self.collected_pages.append(page)
                await context.enqueue_links(strategy=EnqueueStrategy.SAME_DOMAIN)

        await crawler.run([request.url])
        return self.collected_pages

    async def _process_page(self, context: BeautifulSoupCrawlingContext) -> DocPage | None:
        soup = context.soup
        body = soup.find('body')
        if not body:
            return None

        for tag in body.find_all(['script', 'style', 'noscript']): # type: ignore
            tag.decompose()

        md_content = self.md_converter.handle(str(body))
        title = soup.title.string if soup.title else "Untitled"

        return DocPage(
            url=context.request.url,
            title=title, # type: ignore
            content=md_content,
            headings=[h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])]
        )
