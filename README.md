# Crawlee Web Crawler Connector

A web crawler connector for Elasticsearch using the [Crawlee](https://crawlee.dev/) Python library.

## Overview

This connector crawls websites starting from configurable seed URLs and extracts page content into Elasticsearch. It uses BeautifulSoupCrawler for HTML parsing and supports domain filtering, depth control, and URL exclusion patterns.

## Features

- 🌐 Configurable seed URLs and allowed domains
- 📏 Depth-limited crawling from seed pages
- 🚫 URL exclusion patterns
- 🤖 Respects robots.txt (configurable)
- 📝 Extracts clean text content from HTML
- 🏷️ Captures page metadata (title, keywords, description, author)
- 🔄 Page limit controls to prevent runaway crawls

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `seed_urls` | list | Yes | - | Starting URLs for the crawl |
| `allowed_domains` | list | No | [] (all allowed) | Restrict crawling to these domains |
| `max_crawl_depth` | int | No | 3 | Maximum link depth from seed URLs (0 = seed URLs only) |
| `max_pages` | int | No | 1000 | Maximum total pages to crawl |
| `respect_robots_txt` | bool | No | true | Honor robots.txt exclusion rules |
| `exclude_patterns` | list | No | [] | URL patterns to skip (substring match) |
| `user_agent` | str | No | (Crawlee default) | Custom User-Agent string |

### Example Configuration

```yaml
seed_urls:
  - https://example.com
  - https://example.com/docs
allowed_domains:
  - example.com
  - www.example.com
max_crawl_depth: 2
max_pages: 500
respect_robots_txt: true
exclude_patterns:
  - /admin
  - /login
  - .pdf
user_agent: MyCustomCrawler/1.0
```

## Document Schema

Each crawled page produces a document with the following fields:

```json
{
  "_id": "SHA256 hash of URL",
  "_timestamp": "ISO 8601 timestamp of crawl",
  "url": "Full page URL",
  "title": "Page title from <title> tag",
  "keywords": "Meta keywords (if present)",
  "description": "Meta description (if present)",
  "author": "Meta author (if present)",
  "text": "Clean text content (scripts/styles/nav/footer removed)",
  "depth": 0,
  "domain": "hostname",
  "type": "webpage"
}
```

## Usage

### Via Kibana UI

1. Navigate to **Stack Management** → **Connectors**
2. Create a new connector with service type **Crawlee Web Crawler**
3. Configure the seed URLs and crawler settings
4. Create a sync job to start crawling

### Via CLI

1. **Create connector**:
   ```bash
   connectors connector create \
     --index-name my-website-crawl \
     --service-type crawlee \
     --name "My Website Crawler"
   ```

2. **Configure via Kibana UI** or Elasticsearch API

3. **Run connector service**:
   ```bash
   elastic-ingest --config-file config.yml
   ```

### Via Configuration File

Create a `config.yml`:

```yaml
elasticsearch:
  host: https://your-es-cluster:443
  api_key: your-api-key

connectors:
  - connector_id: your-connector-id
    service_type: crawlee

sources:
  crawlee: connectors.sources.crawlee:CrawleeDataSource
```

Then run:
```bash
elastic-ingest --config-file config.yml
```

## How It Works

1. **Initialization**: Crawler starts with configured seed URLs
2. **Crawling**: For each page:
   - Fetches HTML content
   - Checks domain and exclusion rules
   - Verifies depth limit
   - Extracts text and metadata
   - Discovers links for further crawling
3. **Indexing**: Documents are yielded to the framework for bulk indexing
4. **Completion**: Stops when max_pages reached or no more URLs to crawl

## Depth Calculation

Depth is calculated as the number of path segments beyond the seed URL:
- Seed URL: `https://example.com/docs` → depth 0
- `/docs/guide` → depth 1
- `/docs/guide/setup` → depth 2

## Text Extraction

The connector extracts clean text by:
1. Removing `<script>`, `<style>`, `<nav>`, `<footer>` elements
2. Extracting text with `get_text()`
3. Cleaning up whitespace and formatting
4. Producing Markdown-like output

## Limitations

- Uses BeautifulSoupCrawler (no JavaScript execution)
- For JavaScript-heavy sites, consider using Playwright-based crawlers
- Crawlee respects politeness delays between requests
- Large crawls may take significant time

## Dependencies

- `crawlee[beautifulsoup]==1.2.1`
- Python 3.10-3.11

## Development

See the main connectors framework documentation for:
- Running tests: `make test`
- Linting: `make lint`
- Development setup: `make install`

Tests are located in `tests/sources/test_crawlee.py`.

## Support

This connector is part of the Elasticsearch Connectors framework. For issues or questions:
- Framework documentation: See main README
- Crawlee documentation: https://crawlee.dev/
