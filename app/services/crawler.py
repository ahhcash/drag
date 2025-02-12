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
            # Write HTML to temp file for UnstructuredHTMLLoader
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html") as tmp:
                tmp.write(str(context.soup))
                tmp.flush()

                # Use UnstructuredHTMLLoader in elements mode
                loader = UnstructuredHTMLLoader(
                    tmp.name, mode="elements", strategy="fast"
                )
                elements = loader.load()

                # Reconstruct content while preserving structure
                content_parts = []
                title = "Untitled"
                headings = []

                for elem in elements:
                    elem_type = elem.metadata.get("category", "")
                    text = elem.page_content.strip()

                    if not text:
                        continue

                    if elem_type == "Title":
                        if not title or title == "Untitled":
                            title = text
                        headings.append(text)
                        content_parts.append(f"\n## {text}\n")

                    elif elem_type == "NarrativeText":
                        content_parts.append(text)

                    elif elem_type == "ListItem":
                        content_parts.append(f"• {text}")

                    elif elem_type == "Code":
                        content_parts.append(f"```\n{text}\n```")

                    # Handle other element types as needed

                # Join all parts with proper spacing
                content = "\n\n".join(
                    part.strip() for part in content_parts if part.strip()
                )

                # Extract page title if not found in elements
                if title == "Untitled" and context.soup.title:
                    if context.soup.title.string:
                        title = context.soup.title.string

                return DocPage(
                    url=context.request.url,
                    title=title,
                    content=content,
                    headings=headings,
                )

        except Exception as e:
            logger.error(f"failed to process page {context.request.url}: {str(e)}")
            return None
