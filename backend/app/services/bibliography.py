"""
SourceLens — Bibliography Extractor
Detects and parses bibliography/reference sections from source documents.
"""

import re
import json
import logging
from app.models import BibEntry, SourceType, ReliabilityTier
from app.prompts.templates import BIBLIOGRAPHY_EXTRACTION_PROMPT
from app.services.llm_client import llm_generate, parse_json_response, has_api_key
from app.config import get_settings

logger = logging.getLogger(__name__)


def detect_bibliography_section(text: str) -> str | None:
    """
    Detect and extract the bibliography/references section from document text.
    Returns the bibliography text if found, None otherwise.
    """
    # Common bibliography section headers
    patterns = [
        r'(?:^|\n)\s*(?:References|Bibliography|Sources|Works Cited|Notes|Reference List|Citations)\s*\n',
        r'(?:^|\n)\s*#{1,3}\s*(?:References|Bibliography|Sources|Works Cited)\s*\n',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Extract from the header to the end of the document
            bib_text = text[match.start():]
            # Limit to a reasonable size (bibliographies rarely exceed 10000 chars)
            if len(bib_text) > 10000:
                bib_text = bib_text[:10000]
            return bib_text.strip()

    # Also try to detect numbered reference patterns at the end of the document
    # Look for patterns like [1], [2], etc. in the last 30% of the document
    last_portion = text[int(len(text) * 0.7):]
    ref_pattern = re.compile(r'^\s*\[(\d+)\]', re.MULTILINE)
    refs = list(ref_pattern.finditer(last_portion))
    if len(refs) >= 3:  # At least 3 numbered references
        return last_portion[refs[0].start():].strip()

    return None


async def extract_bibliography(text: str) -> list[BibEntry]:
    """
    Extract bibliography entries from document text using regex + LLM fallback.
    """
    bib_section = detect_bibliography_section(text)
    if not bib_section:
        return []

    # Try regex-based extraction first
    entries = _regex_extract(bib_section)

    # If regex found few or no entries, use LLM
    if len(entries) < 2:
        entries = await _llm_extract(bib_section)

    logger.info(f"Extracted {len(entries)} bibliography entries")
    return entries


def _regex_extract(bib_text: str) -> list[BibEntry]:
    """Attempt to parse bibliography entries using regex patterns."""
    entries = []

    # Pattern 1: Numbered references like [1] ... or 1. ...
    pattern = re.compile(r'^\s*\[?(\d+)[\].]?\s+(.+?)(?=^\s*\[?\d+[\].]?\s|\Z)', re.MULTILINE | re.DOTALL)

    for match in pattern.finditer(bib_text):
        ref_id = f"[{match.group(1)}]"
        ref_text = match.group(2).strip().replace('\n', ' ')

        # Try to extract structured info
        year_match = re.search(r'\((\d{4})\)|\b(20[0-2]\d|19\d{2})\b', ref_text)
        url_match = re.search(r'https?://\S+', ref_text)

        entries.append(BibEntry(
            ref_id=ref_id,
            ref_text=ref_text,
            year=year_match.group(1) or year_match.group(2) if year_match else "",
            url=url_match.group(0) if url_match else "",
            source_type=SourceType.UNKNOWN,
            reliability_tier=ReliabilityTier.UNKNOWN,
        ))

    return entries


async def _llm_extract(bib_text: str) -> list[BibEntry]:
    """Use LLM to parse bibliography entries."""
    if not has_api_key():
        return []

    prompt = BIBLIOGRAPHY_EXTRACTION_PROMPT.format(bibliography_text=bib_text[:5000])

    try:
        text = await llm_generate(
            prompt=prompt,
            system_prompt="You are a citation parser. Respond with valid JSON only.",
            temperature=0.1,
        )

        data = parse_json_response(text)
        if not isinstance(data, list):
            return []

        entries = []
        for item in data:
            try:
                source_type = SourceType.UNKNOWN
                try:
                    source_type = SourceType(item.get("source_type", "unknown"))
                except ValueError:
                    pass

                entries.append(BibEntry(
                    ref_id=item.get("ref_id", ""),
                    ref_text=item.get("full_text", ""),
                    authors=item.get("authors", ""),
                    title=item.get("title", ""),
                    publication=item.get("publication", ""),
                    year=item.get("year", ""),
                    url=item.get("url", ""),
                    source_type=source_type,
                ))
            except Exception:
                continue

        return entries

    except Exception as e:
        logger.error(f"LLM bibliography extraction failed: {e}")
        return []
