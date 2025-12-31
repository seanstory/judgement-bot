#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Crawlee connector for web crawling and scraping.

This connector uses the Crawlee library to crawl websites starting from seed URLs
and extract page content in a structured format.
"""
import hashlib
from datetime import datetime

from connectors_sdk.source import BaseDataSource

from connectors.sources.crawlee.client import CrawleeClient


class CrawleeDataSource(BaseDataSource):
    """Crawlee connector for web crawling"""

    name = "Crawlee Web Crawler"
    service_type = "crawlee"
    incremental_sync_enabled = False
    dls_enabled = False
    advanced_rules_enabled = False

    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.client = CrawleeClient(configuration=configuration)

    def _set_internal_logger(self):
        """Set logger for internal client"""
        self.client.set_logger(self._logger)

    @classmethod
    def get_default_configuration(cls):
        """Return default configuration for Crawlee connector"""
        return {
            "seed_urls": {
                "label": "Seed URLs",
                "order": 1,
                "type": "list",
                "tooltip": "Starting URLs for the web crawl. The crawler will begin from these URLs and follow links.",
                "display": "textarea",
                "required": True,
            },
            "allowed_domains": {
                "label": "Allowed domains",
                "order": 2,
                "type": "list",
                "tooltip": "Optional list of domains to restrict crawling to. If empty, all domains are allowed. Example: example.com, subdomain.example.com",
                "display": "textarea",
                "required": False,
            },
            "max_crawl_depth": {
                "label": "Maximum crawl depth",
                "order": 3,
                "type": "int",
                "display": "numeric",
                "tooltip": "Maximum depth of links to follow from seed URLs. 0 means only crawl seed URLs.",
                "default_value": 3,
                "required": False,
            },
            "max_pages": {
                "label": "Maximum pages to crawl",
                "order": 4,
                "type": "int",
                "display": "numeric",
                "tooltip": "Maximum total number of pages to crawl across all seed URLs.",
                "default_value": 1000,
                "required": False,
            },
            "respect_robots_txt": {
                "label": "Respect robots.txt",
                "order": 5,
                "type": "bool",
                "display": "toggle",
                "tooltip": "Whether to respect robots.txt exclusion rules.",
                "default_value": True,
                "required": False,
            },
            "exclude_patterns": {
                "label": "URL exclude patterns",
                "order": 6,
                "type": "list",
                "tooltip": "Optional list of URL patterns to exclude from crawling. URLs containing any of these strings will be skipped.",
                "display": "textarea",
                "required": False,
            },
            "user_agent": {
                "label": "Custom User Agent",
                "order": 7,
                "type": "str",
                "tooltip": "Optional custom User-Agent string to use when crawling. If empty, Crawlee's default will be used.",
                "required": False,
            },
        }

    async def ping(self):
        """Test the connection to seed URLs"""
        self._logger.info("Testing connection by crawling first seed URL")
        try:
            await self.client.ping()
            self._logger.info("Successfully connected and crawled test URL")
        except Exception as e:
            self._logger.error(f"Ping failed: {e}")
            raise

    async def validate_config(self):
        """Validate connector configuration"""
        await super().validate_config()

        # Validate seed URLs
        seed_urls = self.configuration.get("seed_urls", [])
        if not seed_urls:
            msg = "At least one seed URL must be configured"
            raise ValueError(msg)

        # Validate URLs are properly formatted
        for url in seed_urls:
            if not url.startswith(("http://", "https://")):
                msg = f"Invalid seed URL: {url}. URLs must start with http:// or https://"
                raise ValueError(msg)

        # Validate max_crawl_depth
        max_depth = self.configuration.get("max_crawl_depth", 3)
        if max_depth < 0:
            msg = f"max_crawl_depth must be >= 0, got {max_depth}"
            raise ValueError(msg)

        # Validate max_pages
        max_pages = self.configuration.get("max_pages", 1000)
        if max_pages < 1:
            msg = f"max_pages must be >= 1, got {max_pages}"
            raise ValueError(msg)

    def _generate_doc_id(self, url):
        """Generate a unique document ID from URL"""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    async def get_docs(self, filtering=None):
        """Crawl pages and yield documents

        Args:
            filtering: Optional filtering rules (not used in this connector)

        Yields:
            Tuple of (document dict, None) for each crawled page
        """
        self._logger.info("Starting web crawl")

        # Crawl pages using the client
        pages = await self.client.crawl_pages()

        self._logger.info(f"Crawl complete, yielding {len(pages)} documents")

        # Yield each page as a document
        for page in pages:
            doc = {
                "_id": self._generate_doc_id(page["url"]),
                "_timestamp": datetime.utcnow().isoformat(),
                "url": page["url"],
                "title": page["title"],
                "keywords": page["keywords"],
                "description": page["description"],
                "author": page.get("author", ""),
                "text": page["text"],
                "depth": page["depth"],
                "domain": page["domain"],
                "type": "webpage",
            }

            yield doc, None

    async def close(self):
        """Close the connector and cleanup resources"""
        await self.client.close()
