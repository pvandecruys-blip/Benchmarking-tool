"""
SourceLens — Citation Chain Tracer  
Follows citation references from source documents to their ultimate original sources.
"""

import re
import logging
from app.models import CitationChain, FileRef, BibEntry

logger = logging.getLogger(__name__)


def trace_citation_chain(
    matched_text: str,
    matched_doc: FileRef,
    llm_chain: CitationChain | None = None,
) -> CitationChain:
    """
    Trace the citation chain from a matched source passage to its ultimate source.
    
    Combines:
    1. Reference markers found in the matched text (e.g., [1], [28])
    2. Bibliography entries from the source document
    3. LLM-identified attribution from verification step
    """
    # If LLM already found a chain, enhance it with bibliography data
    if llm_chain and llm_chain.ultimate_source:
        # Try to match the intermediate ref to a bibliography entry
        if llm_chain.intermediate_ref_id and matched_doc.bibliography_entries:
            bib = _find_bib_entry(matched_doc.bibliography_entries, llm_chain.intermediate_ref_id)
            if bib:
                return CitationChain(
                    intermediate_source=matched_doc.document_label or matched_doc.original_filename,
                    intermediate_ref_id=llm_chain.intermediate_ref_id,
                    ultimate_source=bib.title or bib.ref_text or llm_chain.ultimate_source,
                    ultimate_source_type=bib.source_type.value if bib.source_type else llm_chain.ultimate_source_type,
                    ultimate_source_url=bib.url or llm_chain.ultimate_source_url,
                )
        return llm_chain

    # Try to find reference markers in the matched text
    ref_pattern = re.compile(
        r'\[(\d+)\]'
        r'|\(ref\s*\[?(\d+)\]?\)'
        r'|\(([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&\s+[A-Z][a-z]+))*,?\s*\d{4})\)',
    )

    refs_found = list(ref_pattern.finditer(matched_text))

    if refs_found and matched_doc.bibliography_entries:
        for ref_match in refs_found:
            ref_id = ref_match.group(1) or ref_match.group(2)
            if ref_id:
                bib = _find_bib_entry(matched_doc.bibliography_entries, f"[{ref_id}]")
                if bib:
                    return CitationChain(
                        intermediate_source=matched_doc.document_label or matched_doc.original_filename,
                        intermediate_ref_id=f"[{ref_id}]",
                        ultimate_source=bib.title or bib.ref_text,
                        ultimate_source_type=bib.source_type.value if bib.source_type else "unknown",
                        ultimate_source_url=bib.url or None,
                    )
            # Handle author-year citations like (McKinsey, 2024)
            author_year = ref_match.group(3)
            if author_year:
                return CitationChain(
                    intermediate_source=matched_doc.document_label or matched_doc.original_filename,
                    intermediate_ref_id=f"({author_year})",
                    ultimate_source=author_year,
                    ultimate_source_type="unknown",
                )

    # No citation chain found — the matched document IS the source
    return CitationChain(
        intermediate_source=None,
        intermediate_ref_id=None,
        ultimate_source=matched_doc.document_label or matched_doc.original_filename,
        ultimate_source_type=_classify_doc_type(matched_doc),
    )


def _find_bib_entry(entries: list[BibEntry], ref_id: str) -> BibEntry | None:
    """Find a bibliography entry by reference ID."""
    # Normalize the ref_id
    ref_num = re.search(r'(\d+)', ref_id)
    if not ref_num:
        return None

    target = ref_num.group(1)
    for entry in entries:
        entry_num = re.search(r'(\d+)', entry.ref_id)
        if entry_num and entry_num.group(1) == target:
            return entry
    return None


def _classify_doc_type(doc: FileRef) -> str:
    """Classify document type string from FileRef."""
    type_map = {
        "deep_research_report": "industry_report",
        "article": "news_article",
        "whitepaper": "consultancy_publication",
        "market_research": "industry_report",
        "regulatory_document": "regulatory_document",
        "internal_analysis": "company_publication",
    }
    return type_map.get(doc.document_type.value, "unknown")
