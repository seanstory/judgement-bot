#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Crawlee client for web crawling and scraping"""
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from connectors_sdk.logger import logger
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext


class CrawleeClient:
    """Client for crawling web pages using Crawlee"""

    def __init__(self, configuration):
        self._logger = logger
        self.seed_urls = configuration.get("seed_urls", [])
        self.allowed_domains = configuration.get("allowed_domains", [])
        self.max_crawl_depth = configuration.get("max_crawl_depth", 3)
        self.max_pages = configuration.get("max_pages", 1000)
        self.respect_robots_txt = configuration.get("respect_robots_txt", True)
        self.exclude_patterns = configuration.get("exclude_patterns", [])
        self.user_agent = configuration.get("user_agent")

        self._page_count = 0
        self._pages_data = []

    def set_logger(self, logger_):
        """Set the logger for this client"""
        self._logger = logger_

    async def ping(self):
        """Test connectivity by attempting to crawl the first seed URL"""
        if not self.seed_urls:
            msg = "No seed URLs configured"
            raise ValueError(msg)

        try:
            # Simple test - just verify we can create a crawler
            crawler = PlaywrightCrawler(
                max_requests_per_crawl=1,
                request_handler=self._create_request_handler(),
                headless=True,
            )
            # Test with first seed URL only
            await crawler.run([self.seed_urls[0]])
            return True
        except Exception as e:
            self._logger.error(f"Ping failed: {e}")
            raise

    def _is_allowed_url(self, url):
        """Check if URL is allowed based on domain restrictions"""
        if not self.allowed_domains:
            return True

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for allowed in self.allowed_domains:
            allowed_lower = allowed.lower()
            if domain == allowed_lower or domain.endswith(f".{allowed_lower}"):
                return True

        return False

    def _should_exclude_url(self, url):
        """Check if URL matches any exclude patterns"""
        if not self.exclude_patterns:
            return False

        for pattern in self.exclude_patterns:
            if pattern in url:
                return True

        return False

    def _extract_text_from_soup(self, soup):
        """Extract clean text from BeautifulSoup object as Markdown-like format"""
        # Find the main element
        main_element = soup.select_one('main')

        # If no main element exists, fall back to body
        if not main_element:
            main_element = soup.select_one('body')

        # If still nothing, use the whole soup
        if not main_element:
            main_element = soup

        # Remove script and style elements from the main content
        for element in main_element(["script", "style"]):
            element.decompose()

        # Get text and clean it up
        text = main_element.get_text(separator="\n", strip=True)
        # Remove excessive newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n\n".join(lines)

    def _extract_metadata(self, soup):
        """Extract metadata from page"""
        metadata = {}

        # Extract meta keywords
        keywords_tag = soup.find("meta", attrs={"name": "keywords"})
        if keywords_tag and keywords_tag.get("content"):
            metadata["keywords"] = keywords_tag["content"]

        # Extract meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            metadata["description"] = desc_tag["content"]

        # Extract author
        author_tag = soup.find("meta", attrs={"name": "author"})
        if author_tag and author_tag.get("content"):
            metadata["author"] = author_tag["content"]

        return metadata

    def _create_request_handler(self):
        """Create the request handler for Crawlee crawler"""
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            """Handle each crawled page"""
            # Check page limit
            if self._page_count >= self.max_pages:
                return

            url = context.request.url

            # Check if URL is allowed
            if not self._is_allowed_url(url):
                self._logger.debug(f"Skipping URL not in allowed domains: {url}")
                return

            # Check if URL should be excluded
            if self._should_exclude_url(url):
                self._logger.debug(f"Skipping excluded URL: {url}")
                return

            # Calculate depth based on URL path segments from seed URLs
            # For now, use a simple heuristic: count path segments beyond the seed URL
            depth = 0
            for seed_url in self.seed_urls:
                if url.startswith(seed_url):
                    # Count additional path segments beyond the seed
                    seed_path = urlparse(seed_url).path.rstrip('/').split('/')
                    url_path = urlparse(url).path.rstrip('/').split('/')
                    depth = max(0, len(url_path) - len(seed_path))
                    break
            else:
                # URL doesn't start with any seed, estimate depth
                depth = urlparse(url).path.count('/') if urlparse(url).path != '/' else 0

            if depth > self.max_crawl_depth:
                self._logger.debug(f"Skipping URL beyond max depth: {url} (depth: {depth})")
                return

            page = context.page

            # Wait for page to be fully loaded
            await page.wait_for_load_state("networkidle")

            # Capture the INITIAL page content before clicking any buttons
            initial_html = await page.content()
            initial_soup = BeautifulSoup(initial_html, "html.parser")

            # Extract initial metadata and text
            initial_metadata = self._extract_metadata(initial_soup)
            initial_text = self._extract_text_from_soup(initial_soup)

            # Extract title from initial state
            h1_tag = initial_soup.find("h1")
            if h1_tag:
                title = h1_tag.get_text(strip=True)
            else:
                title = initial_soup.title.string if initial_soup.title else ""

            # Accumulate text content from all button clicks
            accumulated_text = []

            # Click ALL buttons on the page to load dynamic content
            # This handles cases where buttons trigger toasts, modals, or inline content
            try:
                # Find all clickable buttons
                all_buttons = await page.locator('button[type="button"]').all()
                # Reverse the order so we click bottom-to-top (avoids dialogs covering buttons)
                all_buttons.reverse()
                self._logger.debug(f"Found {len(all_buttons)} buttons to click (processing bottom to top)")

                for i, button in enumerate(all_buttons):
                    try:
                        # Check if button is visible and enabled
                        if await button.is_visible() and await button.is_enabled():
                            # Get button text for logging
                            button_text = await button.inner_text()
                            self._logger.debug(f"Clicking button {i+1}/{len(all_buttons)}: {button_text}")

                            # Click the button
                            await button.click()

                            # Wait for any dynamic content to load
                            await page.wait_for_timeout(500)

                            # Capture the content that appeared after clicking
                            # Look for modal/toast/overlay content
                            try:
                                # Get the current page HTML after button click
                                current_html = await page.content()
                                current_soup = BeautifulSoup(current_html, "html.parser")

                                # Try to find modal/toast/overlay content
                                # Common selectors for dynamic content containers
                                dynamic_content_selectors = [
                                    '[role="dialog"]',
                                    '[role="alertdialog"]',
                                    '.modal',
                                    '.toast',
                                    '.popover',
                                    '[class*="modal"]',
                                    '[class*="dialog"]',
                                    '[class*="toast"]',
                                    '[class*="popover"]',
                                    '[class*="overlay"]',
                                ]

                                dynamic_content_found = False
                                for selector in dynamic_content_selectors:
                                    elements = current_soup.select(selector)
                                    for element in elements:
                                        # Extract text from the dynamic element
                                        text = element.get_text(separator="\n", strip=True)
                                        if text and len(text) > 10:  # Only capture substantial content
                                            accumulated_text.append(f"\n--- Content from '{button_text}' ---\n{text}")
                                            self._logger.debug(f"Captured {len(text)} chars from dynamic content")
                                            dynamic_content_found = True
                                            break
                                    if dynamic_content_found:
                                        break

                            except Exception as e:
                                self._logger.debug(f"Could not capture dynamic content: {e}")

                            # Now close the modal/toast/overlay
                            try:
                                # Try pressing ESC to close modal
                                await page.keyboard.press('Escape')
                                await page.wait_for_timeout(200)
                            except Exception:
                                pass

                            # Try clicking a close button if it exists
                            close_selectors = [
                                'button:has-text("Close")',
                                'button:has-text("×")',
                                '[aria-label="Close"]',
                                '[class*="close"]',
                                '.modal-close',
                            ]

                            for close_selector in close_selectors:
                                try:
                                    close_btn = page.locator(close_selector).first
                                    if await close_btn.is_visible():
                                        await close_btn.click()
                                        await page.wait_for_timeout(200)
                                        break
                                except Exception:
                                    pass

                    except Exception as e:
                        # Button not clickable or error occurred, continue to next button
                        self._logger.debug(f"Could not click button {i+1}: {e}")
                        continue

            except Exception as e:
                self._logger.warning(f"Error during button clicking: {e}")

            # Use the initial text content and append accumulated dynamic content
            if accumulated_text:
                combined_text = initial_text + "\n\n" + "\n".join(accumulated_text)
                self._logger.debug(f"Added {len(accumulated_text)} dynamic content sections to page text")
            else:
                combined_text = initial_text

            # Create page data using initial metadata and title
            page_data = {
                "url": url,
                "title": title,
                "keywords": initial_metadata.get("keywords", ""),
                "description": initial_metadata.get("description", ""),
                "author": initial_metadata.get("author", ""),
                "text": combined_text,
                "depth": depth,
                "domain": urlparse(url).netloc,
            }

            self._pages_data.append(page_data)
            self._page_count += 1

            self._logger.info(f"Crawled page {self._page_count}/{self.max_pages}: {url} (depth: {depth})")

            # Enqueue links if we haven't reached max depth
            if depth < self.max_crawl_depth and self._page_count < self.max_pages:
                # Enqueue discovered links
                await context.enqueue_links()

        return request_handler

    async def crawl_pages(self):
        """Crawl pages starting from seed URLs"""
        if not self.seed_urls:
            msg = "No seed URLs configured"
            raise ValueError(msg)

        self._page_count = 0
        self._pages_data = []

        # Configure crawler options
        crawler_options = {
            "max_requests_per_crawl": self.max_pages,
            "request_handler": self._create_request_handler(),
            "headless": True,  # Run browser in headless mode
        }

        # Create crawler
        crawler = PlaywrightCrawler(**crawler_options)

        # Run the crawler
        self._logger.info(f"Starting crawl with {len(self.seed_urls)} seed URLs")
        await crawler.run(self.seed_urls)

        self._logger.info(f"Crawl completed. Total pages crawled: {len(self._pages_data)}")

        # Return all crawled pages
        return self._pages_data

    async def close(self):
        """Cleanup resources"""
        self._pages_data = []
