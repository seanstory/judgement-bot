# Hall of Eternal Champions Connector

A specialized connector for indexing Judgement: Eternal Champions game data from the Hall of Eternal Champions website.

## Overview

This connector crawls the [Hall of Eternal Champions](https://www.hallofeternalchampions.com) website to index comprehensive game data for the Judgement tabletop miniatures game. It extracts structured information about gods, tribes, heroes, monsters, summons, artefacts, game definitions, conditions, FAQs, and errata.

## Features

- 🎲 **9 Content Categories**: Automatically crawls all game content types
- 🏛️ **Gods & Tribes**: Divine attributes, champions, avatars, and gifts
- ⚔️ **Heroes**: Stats, weapons, health, abilities, and combat manoeuvres
- 👹 **Monsters & Summons**: Creature types and characteristics
- 🔮 **Artefacts**: Game items and their properties
- 📖 **Game Definitions**: Complete glossary of game terms
- 🎯 **Conditions**: Status effects and their mechanics
- ❓ **FAQs**: Community questions and official answers
- 📝 **Errata**: Rules corrections and updates

## Configuration

This connector requires **no configuration** - it is hardcoded to crawl the Hall of Eternal Champions website. Simply create the connector and run a sync.

## Content Categories

The connector automatically crawls the following sections:

1. **Gods** (`/gods`) - Divine entities and their attributes
2. **Heroes** (`/heroes`) - Playable characters with full stats
3. **Monsters** (`/monsters`) - Enemy creatures
4. **Summons** (`/summons`) - Summonable entities
5. **Artefacts** (`/artefacts`) - In-game items
6. **Game Definitions** (`/gamedefinitions`) - Rules terminology
7. **Conditions** (`/pages/conditions`) - Status effects
8. **FAQs** (`/faqs`) - Frequently asked questions
9. **Errata** (`/errata`) - Rules corrections

## Document Schema

The connector produces **individual documents** for every distinct game element, making all content highly searchable and retrievable. Each definition, condition, ability, FAQ, and erratum gets its own document.

### Common Fields (All Documents)

```json
{
  "_id": "SHA256 hash of URL (or URL#item for sub-items)",
  "_timestamp": "ISO 8601 timestamp of crawl",
  "url": "Page URL (or fragment URL for sub-items)",
  "title": "Document title",
  "text": "Full text content",
  "category": "Document type"
}
```

### Document Categories

**Primary Content Pages:**
- `god`, `tribe` - Divine entities with attributes, champions, avatars
- `hero` - Complete hero pages with stats, weapons, health, abilities
- `monster`, `summon` - Creature pages
- `artefact` - Item pages

**Individual Game Elements** (extracted as separate documents):
- `game_definition` - Individual game term definitions
- `condition` - Individual status effect
- `faq` - Individual FAQ entry
- `erratum` - Individual rules correction
- `innate` - Passive hero ability
- `active` - Activated hero ability
- `combat_manoeuvre` - Special weapon attack

**Summary Pages** (contain full text of all items):
- `game_definitions_page`, `conditions_page`, `faqs_page`, `errata_page`

### Category-Specific Fields

**Gods & Tribes:**
```json
{
  "attributes": ["Aggression", "Impulse", "Intimidation"],
  "champions": ["Hero1", "Hero2"],
  "avatars": ["Avatar1", "Avatar2"]
}
```

**Heroes:**
```json
{
  "difficulty": "Easy",
  "classes": ["Bard"],
  "attributes": {"MOV": 3, "MEL": 6, "RNG": 7, "MAG": 4, "AGI": 0, "RES": 5},
  "weapons": [
    {
      "name": "Sword",
      "type": "MEL",
      "cost": "1AP",
      "reach": "1",
      "glance": "2",
      "solid": "3",
      "crit": "4"
    }
  ],
  "health": {"level_1": 15, "level_2": 16, "level_3": 17},
  "gods": ["Torin", "Humans"],
  "innate_abilities": [],
  "active_abilities": [],
  "combat_manoeuvres": []
}
```

**Monsters & Summons:**
```json
{
  "creature_type": "Demon"
}
```

**Game Definitions:**
```json
{
  "category": "game_definition",
  "title": "Active Player",
  "text": "The player whose turn it is...",
  "source_page": "https://www.hallofeternalchampions.com/gamedefinitions"
}
```

**Conditions:**
```json
{
  "category": "condition",
  "title": "Burn",
  "text": "Takes 3 True Damage at the end...",
  "source_page": "https://www.hallofeternalchampions.com/pages/conditions"
}
```

**FAQs:**
```json
{
  "category": "faq",
  "title": "Can I use Point Blank...",
  "text": "Question and answer combined",
  "question": "Can I use Point Blank...",
  "answer": "Yes, you can...",
  "source_page": "https://www.hallofeternalchampions.com/faqs"
}
```

**Errata:**
```json
{
  "category": "erratum",
  "title": "Errata: Demon Tax",
  "text": "Correction text...",
  "item_name": "Demon Tax",
  "correction": "When Dor'gokaan is slain...",
  "source_page": "https://www.hallofeternalchampions.com/errata"
}
```

### Ability Documents

**Structure:**
```json
{
  "_id": "sha256_hash",
  "url": "https://www.hallofeternalchampions.com/heroes/bastian#heroic-ballad",
  "title": "Heroic Ballad",
  "text": "Full ability description with mechanics...",
  "category": "innate|active|combat_manoeuvre",
  "cost": "1AP",
  "hero_name": "Bastian",
  "hero_url": "https://www.hallofeternalchampions.com/heroes/bastian"
}
```

### Benefits of Atomic Documents

All game elements (definitions, conditions, FAQs, errata, abilities) are indexed as **individual documents**:

1. **Direct Lookup**: "What is the Burn condition?" returns just that condition
2. **Precise Search**: Find specific ability or definition without parsing lists
3. **Better Relevance**: Each item has its own semantic embedding
4. **Flexible Filtering**: Filter by category, cost, hero, source page
5. **Link Navigation**: `source_page` links back to the full context page
6. **Efficient RAG**: Retrieve exactly what you need for context

## Usage

### Via Kibana UI

1. Navigate to **Stack Management** → **Connectors**
2. Create a new connector with service type **Hall of Eternal Champions**
3. No configuration needed - the connector is ready to use
4. Create and run a sync job to start indexing

### Via CLI

**Create the index with the proper mapping:**

```bash
curl -X PUT "http://localhost:9200/judgement-game-data" \
  -H "Content-Type: application/json" \
  -d @elasticsearch_mapping.json
```

**Create connector:**
```bash
# Use Elasticsearch API or Kibana to create connector
# Service type: hallofeternalchampions
# Index name: judgement-game-data
```

**Run connector service:**
```bash
elastic-ingest --config-file config.yml
```

## How It Works

1. **Category Discovery**: Starts with 9 predefined category URLs
2. **List Page Processing**: For each category:
   - Extracts links to individual detail pages
   - Enqueues detail pages for crawling
   - Parses list pages that contain complete data (conditions, definitions, FAQs, errata)
3. **Detail Page Processing**: For each detail page:
   - Identifies category type from URL
   - Applies category-specific parser
   - Extracts structured data based on page type
4. **Hero Page Special Handling**:
   - Clicks all ability/manoeuvre buttons to open modals
   - Extracts each ability's title, description, and cost
   - Creates separate documents for each ability
   - Categorizes as innate, active, or combat_manoeuvre
   - Links abilities back to hero via `hero_name` and `hero_url`
5. **Dynamic Content**: Uses Playwright to handle JavaScript-rendered content
6. **Document Generation**: Creates Elasticsearch documents with appropriate schema
7. **Indexing**: Yields both page documents and ability documents to the framework

## Parsing Strategy

The connector uses specialized parsers for each category:

- **Gods/Tribes**: Extracts divine attributes, champions, avatars
- **Heroes**: Parses stat tables, weapon data, health values, abilities
- **Monsters/Summons**: Extracts creature types and characteristics
- **Artefacts**: Basic metadata and descriptions
- **Game Definitions**: Array of term/definition pairs
- **Conditions**: Array of condition names and effects
- **FAQs**: Question/answer pairs
- **Errata**: Item corrections and updates

## Technical Details

- **Crawler**: Uses Crawlee with PlaywrightCrawler for JavaScript support
- **HTML Parsing**: BeautifulSoup for DOM navigation and data extraction
- **Document ID**: SHA256 hash of URL for consistent identification
- **Concurrency**: Respects site politeness with controlled request rate

## Dependencies

- `crawlee[playwright]==1.2.1` - Web crawling with JavaScript support
- `beautifulsoup4` - HTML parsing
- Python 3.10-3.11

## Elasticsearch Mapping

An Elasticsearch mapping file is provided in `elasticsearch_mapping.json`. This mapping defines:

- Nested types for weapons, conditions, definitions, FAQs, and errata
- Keyword fields for categorization and filtering
- Text fields with keyword sub-fields for full-text search
- Integer fields for numeric stats

**Apply the mapping before first sync:**
```bash
curl -X PUT "http://localhost:9200/judgement-game-data" \
  -H "Content-Type: application/json" \
  -d @elasticsearch_mapping.json
```

## Example Searches

**Find all heroes for a specific god:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "hero"}},
        {"term": {"gods.keyword": "Torin"}}
      ]
    }
  }
}
```

**Find all heroes with a specific ability (e.g., Point Blank):**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "innate"}},
        {"match": {"title": "Point Blank"}}
      ]
    }
  }
}
```

**Find all 1AP active abilities:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "active"}},
        {"wildcard": {"cost": "1AP*"}}
      ]
    }
  }
}
```

**Find combat manoeuvres for a specific hero:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "combat_manoeuvre"}},
        {"term": {"hero_name.keyword": "Bastian"}}
      ]
    }
  }
}
```

**Find a specific game definition:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "game_definition"}},
        {"match": {"title": "Active Player"}}
      ]
    }
  }
}
```

**Search all conditions:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "term": {"category": "condition"}
  }
}
```

**Find errata for specific item:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "erratum"}},
        {"match": {"item_name": "Demon Tax"}}
      ]
    }
  }
}
```

**Find heroes by difficulty:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "must": [
        {"term": {"category": "hero"}},
        {"term": {"difficulty": "Easy"}}
      ]
    }
  }
}
```

**Semantic search for abilities related to healing:**
```json
GET /judgement-game-data/_search
{
  "query": {
    "bool": {
      "should": [
        {"match": {"text": "heal"}},
        {"match": {"text": "health"}},
        {"match": {"text": "restore"}}
      ],
      "filter": [
        {"terms": {"category": ["innate", "active", "combat_manoeuvre"]}}
      ]
    }
  }
}
```

## Development

See the main connectors framework documentation for:
- Running tests: `make test`
- Linting: `make lint`
- Development setup: `make install`

## Support

This connector is part of the Elasticsearch Connectors framework.
- Framework documentation: See main repository README
- Hall of Eternal Champions: https://www.hallofeternalchampions.com
- Judgement game: https://judgement.game
