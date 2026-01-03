# Hall of Eternal Champions Connector Automation

This directory contains the automation for deploying the Hall of Eternal Champions custom connector using Elastic's connector framework.

## Quick Start

From the `ingestion/` directory, run:

```bash
make connector
```

This will:
1. Create a new timestamped index with the proper mappings
2. Stop any running connector containers
3. Build a custom Docker image with the connector installed
4. Delete all pending sync jobs
5. Update the connector configuration to point to the new index
6. Create a new sync job
7. Run the connectors service and monitor the sync
8. Update the index alias to point to the new index
9. Delete old indices that were replaced
10. Report completion and document count

## Prerequisites

- Docker and Docker Compose installed
- `jq` installed (for JSON processing)
- `.env` file in the repository root with required variables (see below)
- Elasticsearch cluster running and accessible
- Connector already created in Elasticsearch (with ID in `.env`)

## Required Environment Variables

The following variables must be set in the root `.env` file:

```bash
ELASTICSEARCH_URL=https://your-cluster.es.io:443
ELASTICSEARCH_API_KEY=your_api_key_here
CONNECTOR_INDEX_PATTERN=hall-of-champions-*
CONNECTOR_INDEX_ALIAS=hall-of-champions
CONNECTOR_ID=your_connector_id_here
```

## What Gets Created

### Custom Docker Image

The `Dockerfile` creates a custom image based on the official Elastic connectors image that:
- Copies the `hallofeternalchampions/` connector source code into the venv
- Installs the connector's Python dependencies (crawlee, playwright, etc.)
- Installs Chromium system dependencies for web crawling
- Installs Playwright browsers
- Registers the connector in the connectors framework configuration
- Configures the connector to read from environment variables

### Index Pattern

Each run creates a new index with a timestamp suffix:
- Pattern: `hall-of-champions-YYYYMMDD-HHMMSS`
- Example: `hall-of-champions-20260103-143052`

The new index is automatically added to the `hall-of-champions` alias.

## Manual Steps

### Creating the Initial Connector

If you haven't created the connector in Elasticsearch yet:

1. Create the connector via Kibana UI or API
2. Set the service type to `hallofeternalchampions`
3. Note the connector ID and add it to `.env` as `CONNECTOR_ID`

### Cleaning Up Empty Test Indices

The automation automatically deletes old indices that were replaced by the new deployment. However, during testing you may accumulate empty indices. To clean these up:

```bash
make clean-connectors
```

This will delete any indices matching `CONNECTOR_INDEX_PATTERN` that are both empty (0 documents) AND not associated with the `CONNECTOR_INDEX_ALIAS`.

## Troubleshooting

### Build Failures

If Docker build fails, check that:
- `hallofeternalchampions/` directory exists and contains all required files
- `requirements.txt` has valid dependencies
- You have network access to pull the base image

### Sync Failures

If the sync fails, check:
- Connector logs: `docker-compose logs`
- Elasticsearch connector status: Query `.elastic-connectors` index
- Network connectivity to source websites
- API keys and permissions

### Index Creation Failures

If index creation fails:
- Verify `ELASTICSEARCH_URL` and `ELASTICSEARCH_API_KEY` are correct
- Check that the API key has index creation permissions
- Ensure the mapping file is valid JSON

## Architecture

```
ingestion/connector/
├── Dockerfile                       # Custom connector image with Chromium deps
├── docker-compose.yml               # Service definition
├── config.yml                       # Connector config with env var substitution
├── run_connector.sh                 # Main orchestration script
├── clean_connectors.sh              # Cleanup script for empty indices
├── index-mapping.json               # Elasticsearch index mapping
├── .dockerignore                    # Build context exclusions
├── README.md                        # This file
└── hallofeternalchampions/          # Connector source code
    ├── __init__.py
    ├── datasource.py                # Connector data source implementation
    ├── client.py                    # Playwright crawler implementation
    └── requirements.txt             # Python dependencies (crawlee, playwright)
```

## Development

To modify the connector:

1. Edit files in `hallofeternalchampions/`
2. Commit changes to this repo
3. Run `make connector` to test

The connector source in this repo is now the source of truth. No need to manually sync with the Elastic connectors repository.
