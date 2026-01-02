#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Client for crawling Hall of Eternal Champions website"""

from bs4 import BeautifulSoup
from connectors_sdk.logger import logger
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext


class HallOfEternalChampionsClient:
    """Client for crawling Hall of Eternal Champions game data"""

    BASE_URL = "https://www.hallofeternalchampions.com"

    # Category URLs to crawl
    CATEGORIES = {
        "gods": f"{BASE_URL}/gods",
        "heroes": f"{BASE_URL}/heroes",
        "monsters": f"{BASE_URL}/monsters",
        "summons": f"{BASE_URL}/summons",
        "artefacts": f"{BASE_URL}/artefacts",
        "gamedefinitions": f"{BASE_URL}/gamedefinitions",
        "conditions": f"{BASE_URL}/pages/conditions",
        "faqs": f"{BASE_URL}/faqs",
        "errata": f"{BASE_URL}/errata",
    }

    def __init__(self, configuration):
        self._logger = logger
        self._page_count = 0
        self._pages_data = []
        self._ability_documents = {}  # Dict keyed by ability title -> ability doc with entity list
        self._artifact_documents = []  # Artifacts extracted from modals
        self._definition_documents = []  # Game definitions
        self._condition_documents = []  # Conditions
        self._faq_documents = []  # FAQs
        self._errata_documents = []  # Errata items

    def set_logger(self, logger_):
        """Set the logger for this client"""
        self._logger = logger_

    async def ping(self):
        """Test connectivity by attempting to crawl the gods page"""
        return True

    def _create_ping_handler(self):
        """Create a simple request handler for ping"""

        async def ping_handler(context: PlaywrightCrawlingContext) -> None:
            """Handle ping request"""
            await context.page.wait_for_load_state("networkidle")

        return ping_handler

    def _get_category_from_url(self, url):
        """Determine the category type from URL"""
        for category_name, category_url in self.CATEGORIES.items():
            if url.startswith(category_url):
                return category_name
        return "unknown"

    def _extract_list_page_links(self, soup, base_category_url):
        """Extract links to detail pages from a list page"""
        links = []
        # Find all links that start with the category URL
        for link_tag in soup.find_all("a", href=True):
            href = link_tag["href"]
            # Handle relative URLs
            if href.startswith("/"):
                full_url = self.BASE_URL + href
            else:
                full_url = href

            # Only include detail pages (not the category list page itself)
            if full_url.startswith(base_category_url) and full_url != base_category_url:
                links.append(full_url)

        return list(set(links))  # Remove duplicates

    def _extract_common_fields(self, soup, url):
        """Extract fields common to all page types"""
        # Extract title from h1
        h1_tag = soup.find("h1")
        title = h1_tag.get_text(strip=True) if h1_tag else ""

        # Extract image URL - look for main content image
        img_tag = soup.select_one("main img")
        img_url = ""
        if img_tag and img_tag.get("src"):
            src = img_tag["src"]
            img_url = src if src.startswith("http") else self.BASE_URL + src

        # Extract main text content
        main_element = soup.select_one("main")
        if main_element:
            # Remove script and style elements
            for element in main_element(["script", "style"]):
                element.decompose()
            text = main_element.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n\n".join(lines)
        else:
            text = ""

        return {
            "url": url,
            "title": title,
            "img_url": img_url,
            "text": text,
        }

    def _parse_god_page(self, soup, url):
        """Parse a god or tribe detail page"""
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "god" if "/gods/" in url else "tribe"

        # Extract divine attributes (tags/badges showing traits like "Aggression", "Impulse", etc.)
        # These are divs with bg-secondary class near the top of the page
        # Gods typically have 3 attributes, tribes may vary
        # Use "divine_attributes" to avoid conflict with hero "attributes" field (which is an object)
        divine_attributes = []
        for badge in soup.select("div.bg-secondary"):
            badge_text = badge.get_text(strip=True)
            # Filter out non-attribute text (attributes are usually single words or short phrases)
            if badge_text and len(badge_text.split()) <= 2:
                # Avoid duplicates and common UI elements, and cost indicators
                if (
                    badge_text not in divine_attributes
                    and badge_text not in ["Description", "Close", "Free"]
                    and not any(char.isdigit() for char in badge_text)
                ):  # Skip costs like "2S", "3AP"
                    divine_attributes.append(badge_text)
                    # Limit to first 5 badges to avoid picking up artefact costs
                    if len(divine_attributes) >= 5:
                        break
        doc["divine_attributes"] = divine_attributes

        # Extract champions and avatars - look for h3 headings and hero listings beneath them
        champions = []
        avatars = []

        # Find all h3 headings
        for h3 in soup.find_all("h3"):
            heading_text = h3.get_text(strip=True).lower()

            # Determine if this is Avatars or Champions section
            if "avatar" in heading_text:
                # Find all hero links in the next sibling (should be a ul)
                next_elem = h3.find_next_sibling()
                if next_elem:
                    for link in next_elem.select('a[href*="/heroes/"]'):
                        # Extract hero name from the h3 inside the card
                        hero_name_elem = link.find("h3")
                        if hero_name_elem:
                            hero_name = hero_name_elem.get_text(strip=True)
                            if hero_name and hero_name not in avatars:
                                avatars.append(hero_name)

            elif "champion" in heading_text:
                # Find all hero links in the next sibling (should be a ul)
                next_elem = h3.find_next_sibling()
                if next_elem:
                    for link in next_elem.select('a[href*="/heroes/"]'):
                        # Extract hero name from the h3 inside the card
                        hero_name_elem = link.find("h3")
                        if hero_name_elem:
                            hero_name = hero_name_elem.get_text(strip=True)
                            if hero_name and hero_name not in champions:
                                champions.append(hero_name)

        doc["champions"] = champions
        doc["avatars"] = avatars

        return doc

    def _parse_hero_page(self, soup, url, abilities_data=None):
        """Parse a hero detail page

        Args:
            soup: BeautifulSoup object of the page
            url: Page URL
            abilities_data: Optional dict with extracted abilities/manoeuvres from button clicking
        """
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "hero"

        # Extract difficulty - look for it near the difficulty label
        difficulty = ""
        difficulty_elem = soup.find(text=lambda t: t and "Difficulty" in str(t))
        if difficulty_elem:
            # Try to find the actual difficulty value (Easy, Medium, Hard)
            parent = difficulty_elem.parent
            if parent:
                # Look for siblings or nearby text
                for sibling in parent.find_next_siblings():
                    text = sibling.get_text(strip=True)
                    if text in ["Easy", "Medium", "Hard"]:
                        difficulty = text
                        break
                # If not in siblings, check parent's text
                if not difficulty:
                    parent_text = parent.get_text(strip=True)
                    for diff_level in ["Easy", "Medium", "Hard"]:
                        if diff_level in parent_text:
                            difficulty = diff_level
                            break
        doc["difficulty"] = difficulty

        # Extract classes - find h2 with "Classes" and then find divs with the class badges
        classes = []
        for h2 in soup.find_all("h2"):
            if "Classes" in h2.get_text(strip=True):
                # Find the parent div and look for badge divs
                parent_div = h2.parent
                if parent_div:
                    # Look for divs with class information (they have specific styling classes)
                    badges = parent_div.find_all(
                        "div", class_=lambda c: c and "border-transparent" in c
                    )
                    for badge in badges:
                        class_name = badge.get_text(strip=True)
                        if class_name and class_name != "Classes":
                            classes.append(class_name)
                break
        doc["classes"] = classes

        # Extract attributes from table - find h2 "Attributes" then find the table
        attributes = {}
        for h2 in soup.find_all("h2"):
            if "Attributes" in h2.get_text(strip=True):
                # Find the table under this heading
                parent_div = h2.parent
                if parent_div:
                    table = parent_div.find("table")
                    if table:
                        # Get header row for attribute names
                        header_row = (
                            table.find("thead").find("tr")
                            if table.find("thead")
                            else None
                        )
                        if header_row:
                            headers = [
                                th.get_text(strip=True)
                                for th in header_row.find_all("th")
                            ]
                            # Get data row
                            tbody = table.find("tbody")
                            if tbody:
                                data_row = tbody.find("tr")
                                if data_row:
                                    cells = data_row.find_all("td")
                                    for i, cell in enumerate(cells):
                                        if i < len(headers):
                                            attr_name = headers[i]
                                            # Extract value as string (keyword), handle "-" or svg icons
                                            cell_text = cell.get_text(strip=True)
                                            if (
                                                cell_text
                                                and cell_text != "-"
                                                and not cell.find("svg")
                                            ):
                                                # Store as string - Elasticsearch will handle int conversion via subfield
                                                attributes[attr_name] = cell_text
                                            elif cell.find("svg"):
                                                # SVG icon likely means no value (0 or -)
                                                attributes[attr_name] = "-"
                break
        doc["attributes"] = attributes

        # Extract weapons from table - find h2 "Weapons" then find the table
        weapons = []
        for h2 in soup.find_all("h2"):
            if "Weapons" in h2.get_text(strip=True):
                parent_div = h2.parent
                if parent_div:
                    table = parent_div.find("table")
                    if table:
                        # Get header row
                        header_row = (
                            table.find("thead").find("tr")
                            if table.find("thead")
                            else None
                        )
                        if header_row:
                            headers = [
                                th.get_text(strip=True)
                                for th in header_row.find_all("th")
                            ]
                            # Get all weapon rows
                            tbody = table.find("tbody")
                            if tbody:
                                for row in tbody.find_all("tr"):
                                    cells = row.find_all("td")
                                    if len(cells) >= 7:
                                        weapon = {
                                            "name": cells[0].get_text(strip=True),
                                            "type": cells[1].get_text(strip=True),
                                            "cost": cells[2].get_text(strip=True),
                                            "reach": cells[3].get_text(strip=True),
                                            "glance": cells[4].get_text(strip=True),
                                            "solid": cells[5].get_text(strip=True),
                                            "crit": cells[6].get_text(strip=True),
                                        }
                                        weapons.append(weapon)
                break
        doc["weapons"] = weapons

        # Extract health values - find "Health" heading and grid with levels
        health = {}
        for h2 in soup.find_all("h2"):
            h2_text = h2.get_text(strip=True)
            if "Health" in h2_text:
                # Find the parent div
                parent_div = h2.parent
                if parent_div:
                    # Look for the grid with level data
                    grid_div = parent_div.find(
                        "div", class_=lambda c: c and "grid" in c
                    )
                    if grid_div:
                        # Find all level divs
                        level_divs = grid_div.find_all("div", recursive=False)
                        for level_div in level_divs:
                            # Each level div should have a label and a value
                            level_label = level_div.find(
                                "div",
                                class_=lambda c: c and "text-muted-foreground" in c,
                            )
                            level_value = level_div.find(
                                "div", class_=lambda c: c and "font-bold" in c
                            )
                            if level_label and level_value:
                                label_text = level_label.get_text(strip=True)
                                value_text = level_value.get_text(strip=True)
                                # Extract level number from label (e.g., "Level 1" -> 1)
                                import re

                                level_match = re.search(r"Level\s+(\d+)", label_text)
                                if level_match:
                                    level_num = int(level_match.group(1))
                                    try:
                                        health[f"level_{level_num}"] = int(value_text)
                                    except (ValueError, TypeError):
                                        pass
                break
        doc["health"] = health

        # Extract associated gods
        gods = []
        for link in soup.select('a[href*="/gods/"]'):
            god_name = link.get_text(strip=True)
            if god_name:
                gods.append(god_name)
        doc["gods"] = gods

        # Initialize ability arrays (will be filled by button clicking in request handler)
        doc["innate_abilities"] = []
        doc["active_abilities"] = []
        doc["combat_manoeuvres"] = []

        return doc

    def _parse_monster_or_summon_page(self, soup, url, abilities_data=None):
        """Parse a monster or summon detail page

        Args:
            soup: BeautifulSoup object of the page
            url: Page URL
            abilities_data: Optional dict with extracted abilities from button clicking
        """
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "monster" if "/monsters/" in url else "summon"

        # Extract type/classification - look for a subtitle near the title
        # The creature type is usually right after the h1 title
        h1 = soup.find("h1")
        creature_type = ""
        if h1:
            # Look for text near the h1 that might be the creature type
            # It's usually in a nearby element after the h1
            next_elem = h1.find_next_sibling()
            if next_elem:
                text = next_elem.get_text(strip=True)
                # Creature type shouldn't be a heading name like "Attributes"
                if text and text not in [
                    "Attributes",
                    "Weapons",
                    "Health",
                    "Innate Abilities",
                    "Combat Manoeuvres",
                ]:
                    creature_type = text
        doc["creature_type"] = creature_type

        # Extract attributes from table - same structure as heroes
        attributes = {}
        for h2 in soup.find_all("h2"):
            if "Attributes" in h2.get_text(strip=True):
                parent_div = h2.parent
                if parent_div:
                    table = parent_div.find("table")
                    if table:
                        header_row = (
                            table.find("thead").find("tr")
                            if table.find("thead")
                            else None
                        )
                        if header_row:
                            headers = [
                                th.get_text(strip=True)
                                for th in header_row.find_all("th")
                            ]
                            tbody = table.find("tbody")
                            if tbody:
                                data_row = tbody.find("tr")
                                if data_row:
                                    cells = data_row.find_all("td")
                                    for i, cell in enumerate(cells):
                                        if i < len(headers):
                                            attr_name = headers[i]
                                            cell_text = cell.get_text(strip=True)
                                            if (
                                                cell_text
                                                and cell_text != "-"
                                                and not cell.find("svg")
                                            ):
                                                # Store all values as strings - Elasticsearch handles int conversion
                                                attributes[attr_name] = cell_text
                                            elif cell.find("svg"):
                                                # SVG icon means no value
                                                attributes[attr_name] = "0"
                break
        doc["attributes"] = attributes

        # Extract weapons from table - same structure as heroes
        weapons = []
        for h2 in soup.find_all("h2"):
            if "Weapons" in h2.get_text(strip=True):
                parent_div = h2.parent
                if parent_div:
                    table = parent_div.find("table")
                    if table:
                        header_row = (
                            table.find("thead").find("tr")
                            if table.find("thead")
                            else None
                        )
                        if header_row:
                            headers = [
                                th.get_text(strip=True)
                                for th in header_row.find_all("th")
                            ]
                            tbody = table.find("tbody")
                            if tbody:
                                for row in tbody.find_all("tr"):
                                    cells = row.find_all("td")
                                    if len(cells) >= 7:
                                        weapon = {
                                            "name": cells[0].get_text(strip=True),
                                            "type": cells[1].get_text(strip=True),
                                            "cost": cells[2].get_text(strip=True),
                                            "reach": cells[3].get_text(strip=True),
                                            "glance": cells[4].get_text(strip=True),
                                            "solid": cells[5].get_text(strip=True),
                                            "crit": cells[6].get_text(strip=True),
                                        }
                                        weapons.append(weapon)
                break
        doc["weapons"] = weapons

        # Extract health, bounty, tier - monsters have different structure than heroes
        health_value = 0
        bounty_value = ""
        tier_value = 0

        for h2 in soup.find_all("h2"):
            h2_text = h2.get_text(strip=True)
            if "Health" in h2_text or "Bounty" in h2_text:
                parent_div = h2.parent
                if parent_div:
                    # Look for grid or simple divs with labels
                    for div in parent_div.find_all("div", recursive=True):
                        text = div.get_text(strip=True)
                        if "Health" in text and ":" in text:
                            import re

                            match = re.search(r"Health:\s*(\d+)", text)
                            if match:
                                health_value = int(match.group(1))
                        if "Bounty" in text and ":" in text:
                            bounty_text = text.split("Bounty:")[1].strip().split()[0]
                            try:
                                bounty_value = int(bounty_text)
                            except (ValueError, IndexError):
                                bounty_value = bounty_text
                        if "Tier" in text and ":" in text:
                            import re

                            match = re.search(r"Tier:\s*(\d+)", text)
                            if match:
                                tier_value = int(match.group(1))
                break

        # Store health in same format as heroes (level_1, level_2, level_3)
        # For monsters, only set level_1 since they don't level up
        doc["health"] = {"level_1": health_value}
        doc["bounty"] = bounty_value
        doc["tier"] = tier_value

        # Initialize ability arrays (will be filled by button clicking in request handler)
        doc["innate_abilities"] = []
        doc["active_abilities"] = []
        doc["combat_manoeuvres"] = []

        return doc

    def _parse_artefact_page(self, soup, url):
        """Parse an artefact list page (just returns basic page info)"""
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "artefacts_page"

        return doc

    async def _extract_artifacts(self, page, url):
        """Extract individual artifacts by clicking card buttons

        The artifacts page shows cards in a grid. Each card is a button that
        opens a modal with the artifact details.

        Args:
            page: Playwright page object
            url: URL of the artifacts page

        Returns:
            List of artifact documents
        """
        import hashlib

        artifacts = []

        try:
            # Find all buttons on the page
            all_buttons = await page.locator('button[type="button"]').all()
            self._logger.debug(f"Found {len(all_buttons)} buttons on artifacts page")

            # Filter to artifact card buttons (skip filter/UI buttons)
            artifact_buttons = []
            for button in all_buttons:
                try:
                    if await button.is_visible() and await button.is_enabled():
                        button_text = await button.inner_text()
                        # Skip filter/UI buttons
                        if button_text and button_text not in [
                            "All Categories",
                            "All Types",
                            "Clear All",
                            "Close",
                        ]:
                            artifact_buttons.append(button)
                except Exception as e:
                    self._logger.debug(f"Could not check button: {e}")
                    continue

            self._logger.info(
                f"Found {len(artifact_buttons)} artifact cards to process"
            )

            # Click each artifact button and extract modal content
            for i, button in enumerate(artifact_buttons):
                try:
                    # Click the artifact card
                    await button.click()
                    await page.wait_for_timeout(500)

                    # Get modal content
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find modal dialog
                    modal = soup.select_one('[role="dialog"]')
                    if not modal:
                        self._logger.warning(f"No modal found for artifact {i + 1}")
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(200)
                        continue

                    # Extract artifact name from modal title
                    title_elem = modal.find(["h1", "h2", "h3"])
                    artifact_name = (
                        title_elem.get_text(strip=True)
                        if title_elem
                        else f"Artifact {i + 1}"
                    )

                    # Extract full modal text
                    modal_text = modal.get_text(separator="\n", strip=True)

                    # Parse artifact fields from the metadata line
                    # Format: "Type: Offensive | Cost: 1 Fate | Category: Sacred"
                    artifact_type = ""
                    cost = ""
                    artifact_category = ""

                    # Look for the metadata line
                    for line in modal_text.split("\n"):
                        if "|" in line and "Type:" in line:
                            # Parse the pipe-separated fields
                            parts = [p.strip() for p in line.split("|")]
                            for part in parts:
                                if part.startswith("Type:"):
                                    artifact_type = part.replace("Type:", "").strip()
                                elif part.startswith("Cost:"):
                                    cost = part.replace("Cost:", "").strip()
                                elif part.startswith("Category:"):
                                    artifact_category = part.replace(
                                        "Category:", ""
                                    ).strip()
                            break

                    # Extract description (everything after the metadata line, before "Close")
                    description_lines = []
                    found_metadata = False
                    for line in modal_text.split("\n"):
                        if "|" in line and "Type:" in line:
                            found_metadata = True
                            continue
                        if (
                            found_metadata
                            and line.strip()
                            and line.strip() != "Close"
                            and line.strip() != artifact_name
                        ):
                            description_lines.append(line.strip())

                    description = " ".join(description_lines)

                    # Create artifact document
                    artifact_id = hashlib.sha256(
                        f"{url}#{artifact_name}".encode("utf-8")
                    ).hexdigest()
                    artifact_doc = {
                        "_id": artifact_id,
                        "url": f"{url}#{artifact_name.lower().replace(' ', '-')}",
                        "title": artifact_name,
                        "text": modal_text,
                        "category": "artefact",
                        "artifact_type": artifact_type,
                        "cost": cost,
                        "artifact_category": artifact_category,
                        "description": description,
                    }

                    artifacts.append(artifact_doc)
                    self._logger.debug(f"Extracted artifact: {artifact_name}")

                    # Close modal
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(200)

                except Exception as e:
                    self._logger.warning(f"Error extracting artifact {i + 1}: {e}")
                    # Try to close any open modal
                    try:
                        await page.keyboard.press("Escape")
                        await page.wait_for_timeout(200)
                    except Exception as e2:
                        self._logger.debug(f"Could not close modal: {e2}")
                    continue

        except Exception as e:
            self._logger.error(f"Error extracting artifacts from {url}: {e}")

        return artifacts

    def _parse_game_definition_page(self, soup, url):
        """Parse the game definitions page and create individual definition documents"""
        import hashlib

        # Look for definition containers (likely cards or divs)
        for card in soup.select('[class*="card"], [class*="definition"]'):
            name_elem = card.select_one("h2, h3, h4, strong, b")
            if name_elem:
                name = name_elem.get_text(strip=True)
                description = card.get_text(strip=True)

                # Create individual document for each definition
                definition_id = hashlib.sha256(
                    f"{url}#{name}".encode("utf-8")
                ).hexdigest()
                definition_doc = {
                    "_id": definition_id,
                    "url": f"{url}#{name.lower().replace(' ', '-')}",
                    "title": name,
                    "text": description,
                    "category": "game_definition",
                    "source_page": url,
                }

                self._definition_documents.append(definition_doc)

        # Also create a summary page document
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "game_definitions_page"
        return doc

    def _parse_conditions_page(self, soup, url):
        """Parse the conditions page and create individual condition documents"""
        import hashlib

        # Look for condition sections
        for heading in soup.find_all(["h2", "h3"]):
            condition_name = heading.get_text(strip=True)
            if condition_name and condition_name not in ["Conditions", "General Rules"]:
                # Get description from following elements
                description_parts = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    description_parts.append(sibling.get_text(strip=True))

                description = " ".join(description_parts)

                # Create individual document for each condition
                condition_id = hashlib.sha256(
                    f"{url}#{condition_name}".encode("utf-8")
                ).hexdigest()
                condition_doc = {
                    "_id": condition_id,
                    "url": f"{url}#{condition_name.lower().replace(' ', '-')}",
                    "title": condition_name,
                    "text": description,
                    "category": "condition",
                    "source_page": url,
                }

                self._condition_documents.append(condition_doc)

        # Also create a summary page document
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "conditions_page"
        return doc

    def _parse_faq_page(self, soup, url):
        """Parse the FAQs page and create individual FAQ documents"""
        import hashlib

        # Look for question/answer pairs
        for i, elem in enumerate(soup.select('[class*="faq"], [class*="question"]')):
            question = elem.get_text(strip=True)
            answer = ""
            # Try to find answer in next sibling
            if elem.next_sibling:
                answer = elem.next_sibling.get_text(strip=True)

            if question:
                # Create individual document for each FAQ
                faq_id = hashlib.sha256(f"{url}#faq-{i}".encode("utf-8")).hexdigest()
                faq_doc = {
                    "_id": faq_id,
                    "url": f"{url}#faq-{i}",
                    "title": question,
                    "text": f"{question}\n\n{answer}",
                    "category": "faq",
                    "question": question,
                    "answer": answer,
                    "source_page": url,
                }

                self._faq_documents.append(faq_doc)

        # Also create a summary page document
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "faqs_page"
        return doc

    def _parse_errata_page(self, soup, url):
        """Parse the errata page and create individual errata documents"""
        import hashlib

        # Extract errata items
        for heading in soup.find_all(["h2", "h3"]):
            if heading.get_text(strip=True).startswith("Errata:"):
                item_name = heading.get_text(strip=True).replace("Errata:", "").strip()

                # Get description
                description_parts = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ["h2", "h3"]:
                        break
                    description_parts.append(sibling.get_text(strip=True))

                correction = " ".join(description_parts)

                # Create individual document for each erratum
                errata_id = hashlib.sha256(
                    f"{url}#{item_name}".encode("utf-8")
                ).hexdigest()
                errata_doc = {
                    "_id": errata_id,
                    "url": f"{url}#{item_name.lower().replace(' ', '-')}",
                    "title": f"Errata: {item_name}",
                    "text": correction,
                    "category": "erratum",
                    "item_name": item_name,
                    "correction": correction,
                    "source_page": url,
                }

                self._errata_documents.append(errata_doc)

        # Also create a summary page document
        doc = self._extract_common_fields(soup, url)
        doc["category"] = "errata_page"
        return doc

    def _parse_page_by_category(self, soup, url, category):
        """Parse a page based on its category"""
        if category == "gods":
            return self._parse_god_page(soup, url)
        elif category == "heroes":
            return self._parse_hero_page(soup, url)
        elif category in ["monsters", "summons"]:
            return self._parse_monster_or_summon_page(soup, url)
        elif category == "artefacts":
            return self._parse_artefact_page(soup, url)
        elif category == "gamedefinitions":
            return self._parse_game_definition_page(soup, url)
        elif category == "conditions":
            return self._parse_conditions_page(soup, url)
        elif category == "faqs":
            return self._parse_faq_page(soup, url)
        elif category == "errata":
            return self._parse_errata_page(soup, url)
        else:
            # Fallback to common fields
            return self._extract_common_fields(soup, url)

    async def _extract_hero_abilities(self, page, url, hero_name):
        """Extract abilities and combat manoeuvres by clicking buttons

        Returns:
            Dict with innate_abilities, active_abilities, combat_manoeuvres, and accumulated_text
        """
        import re

        abilities_data = {
            "innate_abilities": [],
            "active_abilities": [],
            "combat_manoeuvres": [],
            "accumulated_text": [],  # Text from all modals
        }

        try:
            # First, parse the HTML structure to map button text to ability type
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Create a mapping of button text -> ability type based on HTML structure
            button_to_type = {}

            # Find all h2 headings and their associated buttons
            for h2 in soup.find_all("h2"):
                heading_text = h2.get_text(strip=True).lower()

                # Determine the ability type from the heading
                if "innate" in heading_text:
                    ability_type = "innate"
                elif "active" in heading_text:
                    ability_type = "active"
                elif (
                    "combat" in heading_text
                    or "manoeuvre" in heading_text
                    or "maneuver" in heading_text
                ):
                    ability_type = "combat_manoeuvre"
                else:
                    continue  # Skip other headings

                # Find all buttons under this heading (traverse siblings and children)
                parent_div = h2.parent
                if parent_div:
                    buttons = parent_div.find_all("button", {"type": "button"})
                    for button in buttons:
                        button_text = button.get_text(strip=True)
                        if button_text and "description" not in button_text.lower():
                            button_to_type[button_text] = ability_type
                            self._logger.debug(
                                f"Mapped button '{button_text}' -> {ability_type}"
                            )

            # Find all clickable buttons via Playwright
            all_buttons = await page.locator('button[type="button"]').all()
            self._logger.debug(f"Found {len(all_buttons)} buttons on hero page {url}")

            # Separate description button from others
            description_button = None
            other_buttons = []

            for button in all_buttons:
                try:
                    if await button.is_visible() and await button.is_enabled():
                        button_text = await button.inner_text()
                        button_text = button_text.strip().lower()
                        if "description" in button_text:
                            description_button = button
                        else:
                            other_buttons.append(button)
                except Exception as e:
                    # Button may have become stale or invisible, skip it
                    self._logger.debug(f"Could not process button: {e}")
                    continue

            # Click non-description buttons first (bottom to top, reversed)
            other_buttons.reverse()

            for i, button in enumerate(other_buttons):
                try:
                    if not await button.is_visible() or not await button.is_enabled():
                        continue

                    # Get button text to determine ability name
                    button_text = await button.inner_text()
                    button_text = button_text.strip()

                    if not button_text:
                        continue

                    self._logger.debug(f"Clicking button: {button_text}")

                    # Click the button
                    await button.click()
                    await page.wait_for_timeout(500)

                    # Get the modal/dialog content
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Look for modal content
                    modal_selectors = [
                        '[role="dialog"]',
                        '[role="alertdialog"]',
                        ".modal",
                        '[class*="modal"]',
                        '[class*="dialog"]',
                    ]

                    modal_content = None
                    for selector in modal_selectors:
                        modal_content = soup.select_one(selector)
                        if modal_content:
                            break

                    if modal_content:
                        # Extract ability details
                        ability_title = button_text
                        ability_text = modal_content.get_text(
                            separator="\n", strip=True
                        )

                        # Try to extract cost from the modal title or text
                        cost = ""
                        # Look for cost in format (1AP), (2F), (1S), etc.
                        cost_match = re.search(r"Cost:\s*([^\n]+)", ability_text)
                        if cost_match:
                            cost = cost_match.group(1).strip()
                        elif re.search(r"\((\d+(?:AP|F|S))\)", ability_title):
                            cost_match = re.search(
                                r"\((\d+(?:AP|F|S))\)", ability_title
                            )
                            cost = cost_match.group(1)

                        # Determine ability type from the HTML structure mapping
                        # Use the mapping we built from the DOM structure
                        ability_type = button_to_type.get(ability_title, "innate")
                        self._logger.debug(
                            f"Ability '{ability_title}' categorized as '{ability_type}'"
                        )

                        # Add ability name to appropriate list (for hero document)
                        if ability_type == "innate":
                            abilities_data["innate_abilities"].append(ability_title)
                        elif ability_type == "active":
                            abilities_data["active_abilities"].append(ability_title)
                        elif ability_type == "combat_manoeuvre":
                            abilities_data["combat_manoeuvres"].append(ability_title)

                        # Add modal text to accumulated text
                        abilities_data["accumulated_text"].append(
                            f"\n--- {ability_title} ---\n{ability_text}"
                        )

                        # Add or update consolidated ability document
                        # Use ability title as key (without level/cost info for consolidation)
                        import hashlib

                        # Check if this ability already exists
                        if ability_title in self._ability_documents:
                            # Add this entity to the existing ability's entity list
                            existing_doc = self._ability_documents[ability_title]

                            # Add entity reference if not already present
                            entity_ref = {
                                "name": hero_name,
                                "url": url,
                                "category": "monster"
                                if "/monsters/" in url
                                else ("summon" if "/summons/" in url else "hero"),
                            }

                            if entity_ref not in existing_doc["entities"]:
                                existing_doc["entities"].append(entity_ref)
                        else:
                            # Create new consolidated ability document
                            ability_id = hashlib.sha256(
                                ability_title.encode("utf-8")
                            ).hexdigest()

                            entity_ref = {
                                "name": hero_name,
                                "url": url,
                                "category": "monster"
                                if "/monsters/" in url
                                else ("summon" if "/summons/" in url else "hero"),
                            }

                            ability_doc = {
                                "_id": ability_id,
                                "url": f"#ability-{ability_title.lower().replace(' ', '-').replace('(', '').replace(')', '')}",
                                "title": ability_title,
                                "text": ability_text,
                                "category": ability_type,
                                "cost": cost,
                                "entities": [
                                    entity_ref
                                ],  # List of heroes/monsters that have this ability
                            }

                            self._ability_documents[ability_title] = ability_doc

                    # Close modal
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(200)

                except Exception as e:
                    self._logger.debug(f"Could not process button {i}: {e}")
                    continue

            # Now click the description button last (if it exists)
            if description_button:
                try:
                    self._logger.debug("Clicking description button (last)")
                    await description_button.click()
                    await page.wait_for_timeout(1000)

                    # Get the description content (page changes, not a modal)
                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    # Extract description from main element
                    main_elem = soup.select_one("main")
                    if main_elem:
                        description_text = main_elem.get_text(
                            separator="\n", strip=True
                        )
                        abilities_data["accumulated_text"].append(
                            f"\n--- Description ---\n{description_text}"
                        )

                except Exception as e:
                    self._logger.warning(f"Could not click description button: {e}")

        except Exception as e:
            self._logger.warning(f"Error extracting abilities from {url}: {e}")

        return abilities_data

    def _create_request_handler(self):
        """Create the request handler for Crawlee crawler"""

        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            """Handle each crawled page"""
            url = context.request.url
            page = context.page

            # Determine category first for logging
            category = self._get_category_from_url(url)
            is_list_page = url in self.CATEGORIES.values()

            self._logger.info(
                f"Crawling {'list' if is_list_page else 'detail'} page: {url} (category: {category})"
            )

            # Wait for page to be fully loaded
            await page.wait_for_load_state("networkidle")

            # Additional wait for dynamic content
            await page.wait_for_timeout(1000)

            if is_list_page:
                # Get page content for link extraction
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Special handling for artifacts - extract from modals instead of following links
                if category == "artefacts":
                    self._logger.debug(
                        "Processing artifacts page - extracting from modals"
                    )
                    artifacts = await self._extract_artifacts(page, url)
                    self._artifact_documents.extend(artifacts)
                    self._logger.info(f"Extracted {len(artifacts)} artifacts")

                    # Also save the list page itself
                    page_data = self._parse_page_by_category(soup, url, category)
                    self._pages_data.append(page_data)
                    self._page_count += 1
                else:
                    # For other list pages, extract links to detail pages and enqueue them
                    self._logger.info(f"Processing list page for category: {category}")
                    links = self._extract_list_page_links(soup, url)
                    self._logger.info(
                        f"Found {len(links)} detail page links for {category}"
                    )

                    # Enqueue all detail page links
                    for link in links:
                        await context.add_requests([link])

                    # Also parse the list page itself (for categories like conditions, definitions)
                    if category in ["gamedefinitions", "conditions", "faqs", "errata"]:
                        page_data = self._parse_page_by_category(soup, url, category)
                        self._pages_data.append(page_data)
                        self._page_count += 1
            else:
                # This is a detail page
                self._logger.info(f"Processing detail page for category: {category}")

                # Get INITIAL page content BEFORE clicking any buttons
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Parse initial page state first (this gets weapons, stats, etc.)
                if category == "heroes":
                    page_data = self._parse_hero_page(soup, url, abilities_data=None)
                elif category in ["monsters", "summons"]:
                    page_data = self._parse_monster_or_summon_page(
                        soup, url, abilities_data=None
                    )
                else:
                    page_data = self._parse_page_by_category(soup, url, category)

                # Log the parsed page
                self._logger.info(
                    f"Parsed {page_data.get('category', 'unknown')} page: {page_data.get('title', 'untitled')}"
                )

                # NOW click buttons to get abilities for heroes/monsters/summons
                if category in ["heroes", "monsters", "summons"]:
                    entity_name = page_data.get("title", "Unknown")

                    # Extract abilities by clicking buttons
                    abilities_data = await self._extract_hero_abilities(
                        page, url, entity_name
                    )

                    # Update page data with ability information
                    page_data["innate_abilities"] = abilities_data.get(
                        "innate_abilities", []
                    )
                    page_data["active_abilities"] = abilities_data.get(
                        "active_abilities", []
                    )
                    page_data["combat_manoeuvres"] = abilities_data.get(
                        "combat_manoeuvres", []
                    )

                    # Append accumulated text to page text
                    accumulated_text = abilities_data.get("accumulated_text", [])
                    if accumulated_text:
                        page_data["text"] = (
                            page_data["text"] + "\n\n" + "\n".join(accumulated_text)
                        )

                self._pages_data.append(page_data)
                self._page_count += 1

            self._logger.debug(f"Processed page {self._page_count}: {url}")

        return request_handler

    async def crawl_pages(self):
        """Crawl all categories from Hall of Eternal Champions

        Returns:
            Dict with all document types
        """
        self._page_count = 0
        self._pages_data = []
        self._ability_documents = {}
        self._artifact_documents = []
        self._definition_documents = []
        self._condition_documents = []
        self._faq_documents = []
        self._errata_documents = []

        # Create crawler
        crawler = PlaywrightCrawler(
            max_requests_per_crawl=1000,  # Reasonable limit
            request_handler=self._create_request_handler(),
            headless=True,
        )

        # Start with all category list pages
        seed_urls = list(self.CATEGORIES.values())

        self._logger.info(f"Starting crawl with {len(seed_urls)} category pages")
        self._logger.info(f"Seed URLs: {seed_urls}")
        await crawler.run(seed_urls)

        total_docs = (
            len(self._pages_data)
            + len(self._ability_documents)
            + len(self._artifact_documents)
            + len(self._definition_documents)
            + len(self._condition_documents)
            + len(self._faq_documents)
            + len(self._errata_documents)
        )

        # Count pages by category
        category_counts = {}
        for page in self._pages_data:
            cat = page.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        self._logger.info(
            f"Crawl completed. Pages: {len(self._pages_data)}, "
            f"Abilities: {len(self._ability_documents)}, "
            f"Artifacts: {len(self._artifact_documents)}, "
            f"Definitions: {len(self._definition_documents)}, "
            f"Conditions: {len(self._condition_documents)}, "
            f"FAQs: {len(self._faq_documents)}, "
            f"Errata: {len(self._errata_documents)}, "
            f"Total: {total_docs}"
        )

        # Log page category breakdown
        self._logger.info(f"Page categories: {category_counts}")

        return {
            "pages": self._pages_data,
            "abilities": list(self._ability_documents.values()),  # Convert dict to list
            "artifacts": self._artifact_documents,
            "definitions": self._definition_documents,
            "conditions": self._condition_documents,
            "faqs": self._faq_documents,
            "errata": self._errata_documents,
        }

    async def close(self):
        """Cleanup resources"""
        self._pages_data = []
        self._ability_documents = {}
        self._artifact_documents = []
        self._definition_documents = []
        self._condition_documents = []
        self._faq_documents = []
        self._errata_documents = []
