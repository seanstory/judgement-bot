# Using the Crawlee Web Crawler Connector

This guide shows you how to set up a new web crawler instance using the Crawlee connector.

## Prerequisites

- Elasticsearch cluster with API access
- Python 3.10 or 3.11
- This connectors framework installed

## Quick Start

### 1. Create Your Project Directory

Create a separate directory for your crawler configuration (outside this repository):

```bash
mkdir ~/my-website-crawler
cd ~/my-website-crawler
```

### 2. Copy the Example Configuration

```bash
cp /path/to/connectors/app/connectors_service/connectors/sources/crawlee/example-config.yml ./config.yml
```

### 3. Login to Elasticsearch

```bash
/path/to/connectors/app/connectors_service/.venv/bin/connectors login \
  --host https://your-cluster:443 \
  --method apikey
```

When prompted, enter your API key.

### 4. Create the Connector

```bash
/path/to/connectors/app/connectors_service/.venv/bin/connectors connector create \
  --index-name my-website-crawl \
  --service-type crawlee \
  --name "My Website Crawler"
```

This will output a connector ID. Note this ID for the next step.

### 5. Update Your Configuration

Edit `config.yml` and update:
- `elasticsearch.host` - Your Elasticsearch cluster URL
- `elasticsearch.api_key` - Your API key
- `connectors[0].connector_id` - The connector ID from step 4

### 6. Configure Crawler Settings via Kibana

1. Open Kibana: **Stack Management** → **Connectors**
2. Find your connector by name
3. Click **Configuration** tab
4. Set your crawler parameters:
   - **Seed URLs**: Starting points for your crawl
   - **Allowed Domains**: Restrict to specific domains (optional)
   - **Max Crawl Depth**: How many levels of links to follow
   - **Max Pages**: Maximum pages to crawl
   - Other settings as needed

5. Click **Save configuration**

### 7. Run the Connector Service

```bash
/path/to/connectors/app/connectors_service/.venv/bin/elastic-ingest \
  --config-file config.yml
```

The service will:
- Poll Elasticsearch for sync jobs every 30 seconds
- Execute syncs when triggered
- Log progress to the console

### 8. Trigger a Sync

From Kibana:
1. Navigate to your connector
2. Click **Sync** button
3. Choose **Full sync**

The connector service will pick up the job and start crawling.

## Example Configuration Values

Here's a complete example for crawling a documentation site:

**Seed URLs**:
```
https://docs.example.com/getting-started
https://docs.example.com/api-reference
https://docs.example.com/guides
```

**Allowed Domains**:
```
docs.example.com
example.com
```

**Settings**:
- Max Crawl Depth: `2`
- Max Pages: `1000`
- Respect robots.txt: `true`
- Exclude Patterns: `/admin`, `/login`, `.pdf`

## Monitoring Your Crawl

### View Service Logs

The connector service outputs logs showing:
```
[FMWK] Starting crawl with 3 seed URLs
[FMWK] Crawled page 1/1000: https://docs.example.com/getting-started (depth: 0)
[FMWK] Crawled page 2/1000: https://docs.example.com/installation (depth: 1)
...
[FMWK] Crawl completed. Total pages crawled: 347
```

### Check Sync Status

```bash
/path/to/connectors/app/connectors_service/.venv/bin/connectors connector list
```

### Query Indexed Documents

```bash
curl -X GET "https://your-cluster:443/your-index-name/_search?size=10&pretty" \
  -H "Authorization: ApiKey your-api-key"
```

## File Organization

Keep your instance-specific files separate from the framework:

```
~/my-website-crawler/           # Your project directory
├── config.yml                  # Your connector configuration
├── README.md                   # Project-specific notes
└── .env                        # Optional: environment variables

/path/to/connectors/            # Framework repository (DO NOT commit configs here)
├── app/connectors_service/
│   └── connectors/sources/crawlee/  # Framework code only
```

## Troubleshooting

### Connector Not Found

```
Error: Could not find a connector for service type crawlee
```

**Solution**: Make sure `sources` section in `config.yml` includes:
```yaml
sources:
  crawlee: connectors.sources.crawlee:CrawleeDataSource
```

### No Documents Indexed

**Check**:
1. Connector status in Kibana - should show "Sync complete"
2. Service logs - look for "Crawled page X" messages
3. Seed URLs are accessible
4. Domain restrictions aren't too strict

### Authentication Errors

**Solution**: Re-run login command:
```bash
connectors login --host https://your-cluster:443 --method apikey
```

## Advanced Usage

### Running Specific Sync Types

```bash
# One-time sync
elastic-ingest --config-file config.yml --action sync_content

# Access control sync (if DLS enabled)
elastic-ingest --config-file config.yml --action sync_access_control

# Cleanup old syncs
elastic-ingest --config-file config.yml --action cleanup
```

### Custom User Agent

Set in Kibana connector configuration:
- **Custom User Agent**: `MyBot/1.0 (+https://example.com/bot-info)`

### URL Exclusion Patterns

Exclude common non-content URLs:
```
/admin
/login
/logout
/api/
/cdn-cgi/
.pdf
.zip
.exe
```

## Next Steps

- Set up scheduled syncs in Kibana
- Configure index mappings for your content
- Set up search applications using your crawled data
- Monitor sync performance and adjust `max_pages` as needed

## Support

- Connector documentation: See `README.md` in this directory
- Framework documentation: See main repository README
- Crawlee documentation: https://crawlee.dev/python/
