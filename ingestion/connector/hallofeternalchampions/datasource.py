#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Hall of Eternal Champions connector for Judgement game data.

This connector crawls the Hall of Eternal Champions website to index
game data including gods, tribes, heroes, monsters, summons, artefacts,
game definitions, conditions, FAQs, and errata.
"""

import hashlib
from datetime import datetime

from connectors_sdk.source import BaseDataSource

from connectors.sources.hallofeternalchampions.client import (
    HallOfEternalChampionsClient,
)


class HallOfEternalChampionsDataSource(BaseDataSource):
    """Hall of Eternal Champions connector for Judgement game data"""

    name = "Hall of Eternal Champions"
    service_type = "hallofeternalchampions"
    incremental_sync_enabled = False
    dls_enabled = False
    advanced_rules_enabled = False

    def __init__(self, configuration):
        super().__init__(configuration=configuration)
        self.client = HallOfEternalChampionsClient(configuration=configuration)

    def _set_internal_logger(self):
        """Set logger for internal client"""
        self.client.set_logger(self._logger)

    @classmethod
    def get_default_configuration(cls):
        """Return default configuration for Hall of Eternal Champions connector

        This connector has minimal configuration as it's hardcoded to crawl
        the Hall of Eternal Champions website.
        """
        return {}

    async def ping(self):
        """Test the connection to Hall of Eternal Champions website"""
        self._logger.info("Testing connection to Hall of Eternal Champions")
        try:
            await self.client.ping()
            self._logger.info("Successfully connected to Hall of Eternal Champions")
        except Exception as e:
            self._logger.error(f"Ping failed: {e}")
            raise

    async def validate_config(self):
        """Validate connector configuration"""
        await super().validate_config()
        # No additional validation needed - connector is hardcoded

    def _generate_doc_id(self, url):
        """Generate a unique document ID from URL"""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    async def get_docs(self, filtering=None):
        """Crawl Hall of Eternal Champions and yield documents

        Args:
            filtering: Optional filtering rules (not used in this connector)

        Yields:
            Tuple of (document dict, None) for each crawled page and ability
        """
        self._logger.info("Starting Hall of Eternal Champions crawl")

        # Crawl pages using the client - returns dict with all document types
        crawl_results = await self.client.crawl_pages()
        pages = crawl_results["pages"]
        abilities = crawl_results["abilities"]
        artifacts = crawl_results["artifacts"]
        definitions = crawl_results["definitions"]
        conditions = crawl_results["conditions"]
        faqs = crawl_results["faqs"]
        errata = crawl_results["errata"]

        total_docs = (
            len(pages)
            + len(abilities)
            + len(artifacts)
            + len(definitions)
            + len(conditions)
            + len(faqs)
            + len(errata)
        )

        # Count pages by category for diagnostics
        page_categories = {}
        for page in pages:
            cat = page.get("category", "unknown")
            page_categories[cat] = page_categories.get(cat, 0) + 1

        self._logger.info(
            f"Crawl complete. Pages: {len(pages)}, Abilities: {len(abilities)}, "
            f"Artifacts: {len(artifacts)}, Definitions: {len(definitions)}, "
            f"Conditions: {len(conditions)}, FAQs: {len(faqs)}, "
            f"Errata: {len(errata)}, Total: {total_docs}"
        )
        self._logger.info(f"Page categories breakdown: {page_categories}")

        # Yield each page as a document
        for page in pages:
            # Start with common fields
            doc = {
                "_id": self._generate_doc_id(page["url"]),
                "_timestamp": datetime.utcnow().isoformat(),
                "url": page["url"],
                "title": page["title"],
                "img_url": page.get("img_url", ""),
                "text": page["text"],
                "category": page.get("category", "unknown"),
            }

            # Add category-specific fields
            category = page.get("category")

            if category in ["god", "tribe"]:
                doc["divine_attributes"] = page.get("divine_attributes", [])
                doc["champions"] = page.get("champions", [])
                doc["avatars"] = page.get("avatars", [])

            elif category == "hero":
                doc["difficulty"] = page.get("difficulty", "")
                doc["classes"] = page.get("classes", [])
                doc["attributes"] = page.get("attributes", {})
                doc["weapons"] = page.get("weapons", [])
                doc["health"] = page.get("health", {})
                doc["gods"] = page.get("gods", [])
                doc["innate_abilities"] = page.get("innate_abilities", [])
                doc["active_abilities"] = page.get("active_abilities", [])
                doc["combat_manoeuvres"] = page.get("combat_manoeuvres", [])
                doc["hero_name"] = page.get("title", "")

            elif category in ["monster", "summon"]:
                doc["creature_type"] = page.get("creature_type", "")
                doc["attributes"] = page.get("attributes", {})
                doc["weapons"] = page.get("weapons", [])
                doc["health"] = page.get(
                    "health", {}
                )  # Health is dict with level_1, level_2, level_3
                doc["bounty"] = page.get("bounty", "")
                doc["tier"] = page.get("tier", 0)
                doc["innate_abilities"] = page.get("innate_abilities", [])
                doc["active_abilities"] = page.get("active_abilities", [])
                doc["combat_manoeuvres"] = page.get("combat_manoeuvres", [])

            elif category == "artefact":
                # Artefacts may have additional fields in the future
                pass

            # Summary pages don't need special handling - just yield them
            # Individual items are yielded separately below

            yield doc, None

        # Yield each ability/manoeuvre as a separate document
        # Abilities are now consolidated - one document per unique ability with list of entities
        for ability in abilities:
            ability_doc = {
                "_id": ability["_id"],
                "_timestamp": datetime.utcnow().isoformat(),
                "url": ability["url"],
                "title": ability["title"],
                "text": ability["text"],
                "category": ability["category"],  # innate, active, combat_manoeuvre
                "cost": ability.get("cost", ""),
                "entities": ability.get(
                    "entities", []
                ),  # List of heroes/monsters with this ability
            }
            yield ability_doc, None

        # Yield each artifact as a separate document
        for artifact in artifacts:
            artifact_doc = {
                "_id": artifact["_id"],
                "_timestamp": datetime.utcnow().isoformat(),
                "url": artifact["url"],
                "title": artifact["title"],
                "text": artifact["text"],
                "category": artifact["category"],  # artefact
                "artifact_type": artifact.get("artifact_type", ""),
                "cost": artifact.get("cost", ""),
                "artifact_category": artifact.get("artifact_category", ""),
                "description": artifact.get("description", ""),
            }
            yield artifact_doc, None

        # Yield each game definition as a separate document
        for definition in definitions:
            definition_doc = {
                "_id": definition["_id"],
                "_timestamp": datetime.utcnow().isoformat(),
                "url": definition["url"],
                "title": definition["title"],
                "text": definition["text"],
                "category": definition["category"],  # game_definition
                "source_page": definition.get("source_page", ""),
            }
            yield definition_doc, None

        # Yield each condition as a separate document
        for condition in conditions:
            condition_doc = {
                "_id": condition["_id"],
                "_timestamp": datetime.utcnow().isoformat(),
                "url": condition["url"],
                "title": condition["title"],
                "text": condition["text"],
                "category": condition["category"],  # condition
                "source_page": condition.get("source_page", ""),
            }
            yield condition_doc, None

        # Yield each FAQ as a separate document
        for faq in faqs:
            faq_doc = {
                "_id": faq["_id"],
                "_timestamp": datetime.utcnow().isoformat(),
                "url": faq["url"],
                "title": faq["title"],
                "text": faq["text"],
                "category": faq["category"],  # faq
                "question": faq.get("question", ""),
                "answer": faq.get("answer", ""),
                "source_page": faq.get("source_page", ""),
            }
            yield faq_doc, None

        # Yield each erratum as a separate document
        for erratum in errata:
            erratum_doc = {
                "_id": erratum["_id"],
                "_timestamp": datetime.utcnow().isoformat(),
                "url": erratum["url"],
                "title": erratum["title"],
                "text": erratum["text"],
                "category": erratum["category"],  # erratum
                "item_name": erratum.get("item_name", ""),
                "correction": erratum.get("correction", ""),
                "source_page": erratum.get("source_page", ""),
            }
            yield erratum_doc, None

    async def close(self):
        """Close the connector and cleanup resources"""
        await self.client.close()
