#!/usr/bin/env python3
"""
Parse a board game rulebook PDF into structured JSON chunks for Elasticsearch.
Uses Docling for ML-based document understanding and pypdf for page numbers.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from docling.document_converter import DocumentConverter
from pypdf import PdfReader


def extract_keywords(text: str) -> List[str]:
    """Extract potential keywords from text using simple heuristics."""
    # Extract capitalized terms and acronyms
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    uppercase_terms = re.findall(r'\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b', text)

    keywords = list(set(words + uppercase_terms))
    return sorted(keywords)[:10]


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra whitespace and punctuation."""
    # Remove newlines and extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove common punctuation
    text = re.sub(r'[•\-–—]', '', text)
    return text.strip().lower()


def find_page_number(chunk_text: str, pdf_reader: PdfReader) -> int:
    """
    Find the page number where this chunk's text appears.
    Uses multiple strategies to find the best match.
    """
    # Take first meaningful portion of text
    search_text = chunk_text[:300].strip()
    if len(search_text) < 20:
        return 1  # Default for very short chunks

    # Normalize the search text
    normalized_search = normalize_text(search_text)

    # Extract several word sequences for better matching
    words = normalized_search.split()[:20]  # First 20 words
    if len(words) < 3:
        return 1

    # Try multiple fragment sizes
    fragments = [
        ' '.join(words[:5]),   # First 5 words
        ' '.join(words[:8]),   # First 8 words
        ' '.join(words[2:7]),  # Middle 5 words (skip first 2)
    ]

    # Search through pages
    for page_num, page in enumerate(pdf_reader.pages, start=1):
        try:
            page_text = page.extract_text()
            normalized_page = normalize_text(page_text)

            # Try each fragment
            for fragment in fragments:
                if len(fragment) > 15 and fragment in normalized_page:
                    return page_num
        except:
            continue

    # If still not found, try a more lenient approach with individual words
    # Look for pages containing most of the first 10 words
    best_match_page = 1
    best_match_count = 0

    key_words = words[:10]
    for page_num, page in enumerate(pdf_reader.pages, start=1):
        try:
            page_text = page.extract_text()
            normalized_page = normalize_text(page_text)

            # Count how many key words appear on this page
            match_count = sum(1 for word in key_words if len(word) > 3 and word in normalized_page)

            if match_count > best_match_count:
                best_match_count = match_count
                best_match_page = page_num
        except:
            continue

    # If we found a page with at least 5 matching words, use it
    if best_match_count >= 5:
        return best_match_page

    return 1


def infer_category_from_heading(heading: str) -> str:
    """
    Infer a category from a heading based on content patterns.
    Groups related topics into broader categories.
    """
    heading_lower = heading.lower()

    # Conditions (check first as they're specific)
    if any(word in heading_lower for word in ['burn', 'freeze', 'stun', 'slow', 'poison', 'blind', 'knock down', 'bleed']):
        return 'Tokens and Conditions'

    # Game setup and basics
    if any(word in heading_lower for word in ['setup', 'game set', 'elements', 'components', 'equipment']):
        return 'Game Setup'

    # Hero and character related
    if any(word in heading_lower for word in ['hero', 'warband', 'champion', 'model', 'character', 'draft']):
        return 'Heroes and Models'

    # Combat and actions (including specific actions)
    if any(word in heading_lower for word in ['attack', 'combat', 'melee', 'ranged', 'damage', 'actions available',
                                                'charge', 'parting blow', 'cleave', 'disengage']):
        return 'Combat and Actions'

    # Game mechanics
    if any(word in heading_lower for word in ['phase', 'activation', 'turn', 'round', 'sequence', 'communion']):
        return 'Game Phases'

    # Terrain and positioning
    if any(word in heading_lower for word in ['terrain', 'line of sight', 'shrine', 'pit', 'map', 'forest', 'wall',
                                                'impassable', 'smoke', 'treacherous']):
        return 'Terrain and Maps'

    # Abilities and effects
    if any(word in heading_lower for word in ['ability', 'abilities', 'spell', 'power', 'manoeuvre', 'maneuver']):
        return 'Abilities and Powers'

    # Tokens and markers
    if any(word in heading_lower for word in ['token', 'marker', 'counter', 'condition', 'soul', 'fate']):
        return 'Tokens and Conditions'

    # Monsters
    if any(word in heading_lower for word in ['monster', 'creature', 'demon', 'undead', 'goblin', 'orc']):
        return 'Monsters'

    # Gods and factions
    if any(word in heading_lower for word in ['god', 'effigy', 'krognar', 'allandir', 'brok', 'zaron', 'skoll', 'thorgar', 'trait']):
        return 'Gods and Effigies'

    # Dice and randomness
    if any(word in heading_lower for word in ['dice', 'roll', 'fate dice', 'judgement dice']):
        return 'Dice and Resolution'

    # Special rules
    if any(word in heading_lower for word in ['special', 'unique', 'summoned']):
        return 'Special Rules'

    return 'General Rules'


def build_hierarchical_chunks(doc) -> List[Dict[str, Any]]:
    """
    Build chunks from Docling's document structure.
    Uses markdown export and infers categories from headings.
    """
    chunks = []

    # Get the markdown representation
    markdown_text = doc.export_to_markdown()
    lines = markdown_text.split('\n')

    current_category = None
    current_heading = None
    text_buffer = []

    def save_chunk():
        """Save accumulated text as a chunk if we have content."""
        if text_buffer:
            text = '\n\n'.join(text_buffer).strip()
            # Filter out image placeholders and very short chunks
            text = text.replace('<!-- image -->', '').strip()
            if text and len(text) > 30:
                # Ensure we have both category and title
                category = current_category or "General Rules"
                title = current_heading or category

                chunk = {
                    'category': category,
                    'subcategory': '',
                    'title': title,
                    'text': text,
                    'page_number': 1,  # Docling doesn't easily give us page numbers in markdown
                    'keywords': extract_keywords(text)
                }
                chunks.append(chunk)
        text_buffer.clear()

    for line in lines:
        line = line.strip()
        if not line or line == '<!-- image -->':
            continue

        # Detect markdown headings (Docling uses ## for most headings)
        if line.startswith('##'):
            save_chunk()

            # Extract heading text
            heading_text = line.lstrip('#').strip()
            current_heading = heading_text

            # Infer category from heading
            current_category = infer_category_from_heading(heading_text)

        elif line.startswith('#'):
            # Single # headings are rare but might be major sections
            save_chunk()
            heading_text = line.lstrip('#').strip()
            current_heading = heading_text
            current_category = heading_text  # Use as-is for major sections

        else:
            # Regular content
            if not line.startswith('---'):  # Skip horizontal rules
                text_buffer.append(line)

    # Save final chunk
    save_chunk()

    return chunks


def merge_small_chunks(chunks: List[Dict[str, Any]], min_length: int = 150) -> List[Dict[str, Any]]:
    """
    Merge very small chunks with their neighbors.
    Ensures all chunks have meaningful category and title.
    """
    if not chunks:
        return chunks

    merged = []
    buffer = None

    for chunk in chunks:
        # Ensure chunk has required fields
        if not chunk.get('category'):
            chunk['category'] = 'General'
        if not chunk.get('title'):
            chunk['title'] = chunk.get('category', 'General')

        if buffer is None:
            buffer = chunk
        elif len(buffer['text']) < min_length:
            # Only merge if in same category
            if buffer['category'] == chunk['category']:
                buffer['text'] = buffer['text'] + '\n\n' + chunk['text']
                buffer['keywords'] = list(set(buffer['keywords'] + chunk['keywords']))[:10]
                if not buffer['title'] and chunk['title']:
                    buffer['title'] = chunk['title']
                if not buffer['subcategory'] and chunk['subcategory']:
                    buffer['subcategory'] = chunk['subcategory']
            else:
                merged.append(buffer)
                buffer = chunk
        else:
            merged.append(buffer)
            buffer = chunk

    if buffer:
        merged.append(buffer)

    return merged


def validate_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure all chunks have required fields.
    """
    validated = []
    for idx, chunk in enumerate(chunks, 1):
        # Ensure category is never empty
        if not chunk.get('category') or chunk['category'].strip() == '':
            chunk['category'] = 'General'

        # Ensure title is never empty - use category as fallback
        if not chunk.get('title') or chunk['title'].strip() == '':
            if chunk.get('subcategory'):
                chunk['title'] = chunk['subcategory']
            else:
                chunk['title'] = chunk['category']

        # Ensure subcategory exists (can be empty string)
        if 'subcategory' not in chunk:
            chunk['subcategory'] = ''

        validated.append(chunk)

    return validated


def parse_pdf(pdf_path: Path, output_dir: Path, min_chunk_length: int = 150):
    """
    Parse PDF using Docling and create individual JSON files for each chunk.
    Uses pypdf to find accurate page numbers.
    """
    output_dir.mkdir(exist_ok=True)

    print(f"Parsing with Docling (this may take a minute)...")

    # Convert PDF with Docling
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document

    print(f"Building hierarchical chunks...")
    chunks = build_hierarchical_chunks(doc)

    print(f"Merging small chunks...")
    chunks = merge_small_chunks(chunks, min_chunk_length)

    print(f"Validating chunks...")
    chunks = validate_chunks(chunks)

    print(f"Created {len(chunks)} chunks")

    # Load PDF with pypdf for page number lookup
    print(f"Finding page numbers using pypdf...")
    pdf_reader = PdfReader(str(pdf_path))

    # Update page numbers for each chunk
    for idx, chunk in enumerate(chunks, start=1):
        chunk['page_number'] = find_page_number(chunk['text'], pdf_reader)
        if idx % 50 == 0:
            print(f"  Processed {idx}/{len(chunks)} chunks...")

    print(f"✓ Page numbers updated")

    # Quality check - report any issues
    issues = []
    for idx, chunk in enumerate(chunks, 1):
        if not chunk['category']:
            issues.append(f"Chunk {idx}: Missing category")
        if not chunk['title']:
            issues.append(f"Chunk {idx}: Missing title")

    if issues:
        print(f"\nWARNING: Found {len(issues)} validation issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
    else:
        print("All chunks validated successfully!")

    # Write individual JSON files
    for idx, chunk in enumerate(chunks, 1):
        output_file = output_dir / f"chunk_{idx:04d}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)

    # Create summary
    summary_file = output_dir / "_summary.json"
    summary = {
        'total_chunks': len(chunks),
        'source_pdf': pdf_path.name,
        'categories': sorted(list(set(c['category'] for c in chunks))),
        'validation_issues': len(issues)
    }
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nOutput written to: {output_dir}")
    print(f"Summary: {summary_file}")


def main():
    """Main entry point."""
    pdf_path = Path("JEC-RuleBook-2.6_reduced.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return

    output_dir = Path("output")

    print(f"Parsing: {pdf_path}")
    parse_pdf(pdf_path, output_dir)
    print("\nDone!")


if __name__ == "__main__":
    main()
