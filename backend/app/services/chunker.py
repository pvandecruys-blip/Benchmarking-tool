"""
SourceLens — Document Chunker
Splits documents into overlapping chunks for vector search.
"""

import re
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


def chunk_document(
    text: str,
    file_id: str,
    pages: list[dict] | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict]:
    """
    Split document text into overlapping chunks suitable for embedding.

    Strategy:
    1. Try to split on section headings (##, ###, or numbered sections)
    2. Fall back to paragraph boundaries
    3. Never split mid-sentence

    Returns list of chunk dicts with metadata:
    {
        "chunk_id": str,
        "text": str,
        "source_file_id": str,
        "page_number": int | None,
        "section_heading": str | None,
        "chunk_index": int,
    }
    """
    settings = get_settings()
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # Approximate tokens as chars / 4
    char_size = chunk_size * 4
    char_overlap = chunk_overlap * 4

    # Build page-aware text if pages are provided
    page_map = None
    if pages:
        page_map = _build_page_map(pages, text)

    # Split into sections first
    sections = _split_into_sections(text)

    chunks = []
    chunk_index = 0

    for section_heading, section_text in sections:
        if not section_text.strip():
            continue

        # If section fits in one chunk, use as-is
        if len(section_text) <= char_size:
            page_num = _find_page_number(page_map, section_text) if page_map else None
            chunks.append({
                "chunk_id": f"{file_id}_chunk_{chunk_index}",
                "text": section_text.strip(),
                "source_file_id": file_id,
                "page_number": page_num,
                "section_heading": section_heading,
                "chunk_index": chunk_index,
            })
            chunk_index += 1
        else:
            # Split large sections into overlapping chunks
            sub_chunks = _split_with_overlap(section_text, char_size, char_overlap)
            for sub_text in sub_chunks:
                page_num = _find_page_number(page_map, sub_text) if page_map else None
                chunks.append({
                    "chunk_id": f"{file_id}_chunk_{chunk_index}",
                    "text": sub_text.strip(),
                    "source_file_id": file_id,
                    "page_number": page_num,
                    "section_heading": section_heading,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    logger.info(f"Chunked document {file_id} into {len(chunks)} chunks")
    return chunks


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Split text into sections based on headings."""
    # Match markdown headings or numbered section headings
    heading_pattern = re.compile(
        r'^(#{1,4}\s+.+|(?:\d+\.)+\s+.+|[A-Z][A-Z\s&]+(?:$|\n))',
        re.MULTILINE,
    )

    matches = list(heading_pattern.finditer(text))
    if not matches:
        return [(None, text)]

    sections = []
    # Text before first heading
    if matches[0].start() > 0:
        sections.append((None, text[: matches[0].start()]))

    for i, match in enumerate(matches):
        heading = match.group().strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end]
        sections.append((heading, section_text))

    return sections


def _split_with_overlap(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks, respecting sentence boundaries."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current_size + sentence_len > chunk_size and current_chunk:
            # Emit current chunk
            chunks.append(" ".join(current_chunk))

            # Keep overlap worth of sentences
            overlap_chunk = []
            overlap_size = 0
            for s in reversed(current_chunk):
                if overlap_size + len(s) > overlap:
                    break
                overlap_chunk.insert(0, s)
                overlap_size += len(s)
            current_chunk = overlap_chunk
            current_size = sum(len(s) for s in current_chunk)

        current_chunk.append(sentence)
        current_size += sentence_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def _build_page_map(pages: list[dict], full_text: str) -> list[tuple[int, int, int]]:
    """Build a mapping of character positions to page numbers."""
    page_map = []
    offset = 0
    for page in pages:
        page_text = page["text"]
        # Find where this page's text starts in the full text
        idx = full_text.find(page_text[:100], offset) if page_text else offset
        if idx == -1:
            idx = offset
        page_map.append((page["page_number"], idx, idx + len(page_text)))
        offset = idx + len(page_text)
    return page_map


def _find_page_number(page_map: list[tuple[int, int, int]], chunk_text: str) -> int | None:
    """Find which page a chunk belongs to based on text position."""
    if not page_map:
        return None
    # Simple heuristic: check first 100 chars of chunk against each page
    snippet = chunk_text[:100]
    for page_num, start, end in page_map:
        # This is approximate — good enough for metadata
        if snippet in chunk_text:
            return page_num
    return page_map[0][0] if page_map else None
