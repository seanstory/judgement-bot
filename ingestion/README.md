# Judgement Rulebook Ingestion Tools

Rules search engine for Judgement: Eternal Champions board game.

Parses the official rulebook PDF into structured, searchable chunks and ingests them into Elasticsearch for semantic search.

## Features

- **ML-based PDF parsing** using Docling for intelligent document structure detection
- **Accurate page numbers** using hybrid pypdf approach
- **Smart categorization** into 12 thematic categories
- **Semantic search** ready with `semantic_text` field mappings
- **265 searchable chunks** from 100-page rulebook

## Setup

### Requirements

- Python 3.11+
- Elasticsearch 8.11+ (with API key access)

### Installation

1. Install dependencies:

```bash
make install
```

Or manually:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Parse the Rulebook

Parse the PDF into JSON chunks:

```bash
make run
```

Or manually:
```bash
python3 parse_rulebook.py
```

This creates an `output/` directory with:
- Individual JSON files for each chunk (`chunk_0001.json`, `chunk_0002.json`, etc.)
- A `_summary.json` file with parsing metadata

The parser will:
1. Use Docling to extract structured content and detect headings
2. Intelligently categorize content into thematic groups
3. Find accurate page numbers using pypdf text matching
4. Extract keywords from each chunk
5. Validate that all chunks have category and title fields

### 2. Ingest to Elasticsearch

#### Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Elasticsearch credentials:
```
ELASTICSEARCH_URL=https://your-cluster.es.region.cloud.es.io:443
ELASTICSEARCH_API_KEY=your-api-key-here
ELASTICSEARCH_INDEX=judgement_core_rules
```

#### Ingest Data

```bash
make ingest
```

Or manually:
```bash
python3 ingest.py
```

The ingestion script will:
1. Verify connection to Elasticsearch
2. Create the index if it doesn't exist (using `mappings.json`)
3. Bulk ingest all chunks with 5-minute timeout
4. Verify successful ingestion

### 3. Clean Output

To remove generated JSON files:

```bash
make clean
```

## Data Schema

Each chunk has the following structure:

```json
{
  "category": "Combat and Actions",
  "subcategory": "",
  "title": "Charge Attack",
  "text": "This is a very popular combo move...",
  "page_number": 42,
  "keywords": ["Attack", "Melee", "Combat", "Charge"]
}
```

### Categories

The parser automatically categorizes content into:

- **Combat and Actions** - Attacks, damage, combat mechanics
- **Tokens and Conditions** - Status effects, tokens, markers
- **Terrain and Maps** - Map features, line of sight, shrines
- **Heroes and Models** - Character rules, warbands, drafting
- **Game Phases** - Turn sequence, activation, communion
- **Gods and Effigies** - Deity traits, effigy rules
- **Abilities and Powers** - Special abilities, maneuvers
- **Monsters** - Monster rules and behavior
- **Game Setup** - Initial setup, components
- **Dice and Resolution** - Dice rolling, fate dice
- **Special Rules** - Unique mechanics
- **General Rules** - Everything else

## Elasticsearch Index

### Index Name

`judgement_core_rules` (configurable via `.env`)

### Field Mappings

The index uses specialized field types for semantic search:

- `category`: `semantic_text` - Enables semantic search on categories
- `subcategory`: `semantic_text` - Subcategory semantic search
- `title`: `semantic_text` - Semantic search on chunk titles
- `text`: `semantic_text` - Full semantic search on content
- `keywords`: `keyword` - Exact matching and aggregations
- `page_number`: `integer` - Page reference

Mappings are defined in `mappings.json` and can be customized before index creation.

### Document Count

The Elasticsearch UI may show ~1,069 documents due to internal embedding documents created by `semantic_text` fields. The actual searchable document count is 265 chunks.

## How It Works

### Parsing Pipeline

1. **Docling extraction**: Uses ML models to parse PDF and identify document structure
2. **Markdown conversion**: Exports to markdown preserving heading hierarchy
3. **Category inference**: Pattern-based categorization of sections
4. **Chunk creation**: Groups content under logical headings
5. **Chunk merging**: Combines small fragments for better context
6. **Page number detection**:
   - Extracts text with pypdf from original PDF
   - Matches chunk text using multiple strategies:
     - Exact phrase matching with word sequences
     - Fuzzy matching with keyword counting
     - Best-effort page assignment
7. **Validation**: Ensures all required fields are present
8. **Keyword extraction**: Identifies important terms

### Why Hybrid Approach?

- **Docling**: Superior at understanding document structure and hierarchy
- **pypdf**: Better at preserving exact page locations
- **Combined**: Get the best of both - smart structure + accurate page numbers

## Development

### Make Commands

- `make install` - Install Python dependencies
- `make run` - Parse the rulebook PDF
- `make ingest` - Ingest chunks to Elasticsearch
- `make clean` - Remove output directory

### Adding New Features

The parser is designed to be extensible:

- **Category inference**: Edit `infer_category_from_heading()` to add new categories
- **Index mappings**: Modify `mappings.json` before first ingestion
- **Chunk size**: Adjust `min_chunk_length` parameter in `parse_pdf()`
- **Page detection**: Tune `find_page_number()` for better accuracy

## Troubleshooting

### All page numbers are 1
Run the parser again - the hybrid pypdf approach should find accurate pages.

### Elasticsearch connection fails
- Check your `.env` file has correct credentials
- Verify your API key has index creation permissions
- Ensure the Elasticsearch URL includes the port (usually :443)

### Docling takes too long
Docling uses ML models which can be slow. On a typical laptop:
- Initial model download: ~1 minute (first run only)
- PDF processing: ~75 seconds for 100 pages
- Page number detection: ~5 seconds

### Document count mismatch
The `semantic_text` field creates internal embedding documents. This is expected - your searchable chunks are the 265 source documents.

## Connector

The `connector/` directory contains a Crawlee-based Elasticsearch connector for ingesting web content. See `connector/USAGE.md` for details.

## Credits

- **Judgement: Eternal Champions** - Created by Andrew Galea, reimagined by Creature Caster
- **Docling** - IBM Research's document understanding library
- **pypdf** - PDF text extraction library
