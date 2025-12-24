#!/usr/bin/env python3
"""
Ingest parsed rulebook chunks into Elasticsearch.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers


def load_config() -> Dict[str, str]:
    """Load configuration from .env file."""
    load_dotenv()

    config = {
        'url': os.getenv('ELASTICSEARCH_URL'),
        'api_key': os.getenv('ELASTICSEARCH_API_KEY'),
        'index': os.getenv('ELASTICSEARCH_INDEX', 'judgement_core_rules')
    }

    # Validate required fields
    if not config['url']:
        print("ERROR: ELASTICSEARCH_URL not set in .env file")
        sys.exit(1)
    if not config['api_key']:
        print("ERROR: ELASTICSEARCH_API_KEY not set in .env file")
        sys.exit(1)

    return config


def create_es_client(url: str, api_key: str) -> Elasticsearch:
    """Create and verify Elasticsearch client connection."""
    print(f"Connecting to Elasticsearch at {url}...")

    client = Elasticsearch(
        url,
        api_key=api_key,
        request_timeout=300  # 5 minute timeout
    )

    # Verify connection
    try:
        info = client.info()
        print(f"✓ Connected to Elasticsearch {info['version']['number']}")
        print(f"  Cluster: {info['cluster_name']}")
        return client
    except Exception as e:
        print(f"ERROR: Failed to connect to Elasticsearch: {e}")
        sys.exit(1)


def load_mappings() -> Dict[str, Any]:
    """Load index mappings from mappings.json."""
    mappings_file = Path("mappings.json")
    if not mappings_file.exists():
        print("ERROR: mappings.json not found")
        sys.exit(1)

    with open(mappings_file, 'r') as f:
        return json.load(f)


def ensure_index(client: Elasticsearch, index_name: str, mappings: Dict[str, Any]):
    """Ensure the index exists with correct mappings."""
    if client.indices.exists(index=index_name):
        print(f"✓ Index '{index_name}' already exists")
        return

    print(f"Creating index '{index_name}'...")
    client.indices.create(index=index_name, body=mappings)
    print(f"✓ Index '{index_name}' created successfully")


def load_chunks(output_dir: Path) -> List[Dict[str, Any]]:
    """Load all chunk JSON files from output directory."""
    chunk_files = sorted(output_dir.glob("chunk_*.json"))

    if not chunk_files:
        print(f"ERROR: No chunk files found in {output_dir}")
        sys.exit(1)

    chunks = []
    for chunk_file in chunk_files:
        with open(chunk_file, 'r') as f:
            chunk = json.load(f)
            # Add the chunk ID based on filename
            chunk['_id'] = chunk_file.stem  # e.g., "chunk_0001"
            chunks.append(chunk)

    print(f"✓ Loaded {len(chunks)} chunks from {output_dir}")
    return chunks


def generate_bulk_actions(chunks: List[Dict[str, Any]], index_name: str):
    """Generate bulk index actions for Elasticsearch."""
    for chunk in chunks:
        doc_id = chunk.pop('_id')
        yield {
            '_index': index_name,
            '_id': doc_id,
            '_source': chunk
        }


def ingest_chunks(client: Elasticsearch, chunks: List[Dict[str, Any]], index_name: str):
    """Ingest chunks using bulk API."""
    print(f"\nIngesting {len(chunks)} chunks to '{index_name}'...")

    # Use bulk helper with timeout
    client_with_timeout = client.options(request_timeout=300)
    success, failed = helpers.bulk(
        client_with_timeout,
        generate_bulk_actions(chunks, index_name),
        raise_on_error=False,
        stats_only=False
    )

    if failed:
        print(f"WARNING: {len(failed)} documents failed to index")
        for item in failed[:5]:  # Show first 5 failures
            print(f"  Failed: {item}")
    else:
        print(f"✓ Successfully indexed {success} documents")

    # Refresh index to make documents searchable
    client.indices.refresh(index=index_name)
    print(f"✓ Index refreshed")


def verify_ingestion(client: Elasticsearch, index_name: str, expected_count: int):
    """Verify that documents were ingested correctly."""
    count = client.count(index=index_name)['count']
    print(f"\nVerification:")
    print(f"  Expected documents: {expected_count}")
    print(f"  Actual documents:   {count}")

    if count == expected_count:
        print("✓ Ingestion verified successfully!")
    else:
        print(f"WARNING: Document count mismatch")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Elasticsearch Ingestion Script")
    print("=" * 60)

    # Load configuration
    config = load_config()

    # Create Elasticsearch client
    client = create_es_client(config['url'], config['api_key'])

    # Load mappings
    mappings = load_mappings()

    # Ensure index exists
    ensure_index(client, config['index'], mappings)

    # Load chunks
    output_dir = Path("output")
    chunks = load_chunks(output_dir)

    # Ingest chunks
    ingest_chunks(client, chunks, config['index'])

    # Verify
    verify_ingestion(client, config['index'], len(chunks))

    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
