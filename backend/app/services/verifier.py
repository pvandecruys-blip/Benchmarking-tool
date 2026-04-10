"""
SourceLens — Metric Verifier
Uses LLM to verify extracted metrics against source document chunks.
Supports demo mode with realistic mock verification data.
"""

import json
import random
import logging
from app.models import (
    MetricRecord, Verification, VerificationStatus, MatchedLocation,
    CitationChain, SourceReliability, ReliabilityTier, FileRef
)
from app.prompts.templates import VERIFICATION_PROMPT
from app.services.llm_client import llm_generate, parse_json_response, has_api_key
from app.config import get_settings

logger = logging.getLogger(__name__)


async def verify_metric(
    metric: MetricRecord,
    relevant_chunks: list[dict],
    source_docs: list[FileRef],
) -> Verification:
    """
    Verify a single metric against retrieved source chunks.
    Falls back to demo mode if no API key is configured.
    """
    settings = get_settings()

    if settings.demo_mode or not has_api_key():
        return _generate_demo_verification(metric, relevant_chunks, source_docs)

    if not relevant_chunks:
        return Verification(
            status=VerificationStatus.NOT_FOUND,
            confidence_score=0.0,
            verification_notes="No relevant source passages found",
            llm_reasoning="No source documents provided relevant content for this metric.",
        )

    # Build source excerpts string
    source_excerpts_parts = []
    doc_map = {doc.file_id: doc for doc in source_docs}

    for i, chunk in enumerate(relevant_chunks):
        meta = chunk.get("metadata", {})
        file_id = meta.get("source_file_id", "")
        doc = doc_map.get(file_id)
        doc_name = doc.document_label or doc.original_filename if doc else "Unknown"
        page = meta.get("page_number", "N/A")
        section = meta.get("section_heading", "N/A")

        source_excerpts_parts.append(
            f"[{i+1}. Document: {doc_name}, Page: {page}, Section: {section}]\n"
            f"{chunk['text']}\n---"
        )

    source_excerpts = "\n\n".join(source_excerpts_parts)

    prompt = VERIFICATION_PROMPT.format(
        metric_value=metric.extracted_metric.value,
        metric_description=metric.extracted_metric.description,
        context_sentence=metric.extracted_metric.context_sentence,
        slide_source_tag=metric.slide_source_tag or "None",
        source_excerpts=source_excerpts,
    )

    try:
        response_text = await llm_generate(
            prompt=prompt,
            system_prompt="You are a meticulous fact-checking auditor. Always respond with valid JSON only.",
            temperature=0.1,
        )
        result = parse_json_response(response_text)

        if not isinstance(result, dict):
            return _default_verification("LLM returned non-object response")

        # Parse status
        status_str = result.get("status", "not_found")
        try:
            status = VerificationStatus(status_str)
        except ValueError:
            status = VerificationStatus.NOT_FOUND

        confidence = float(result.get("confidence_score", 0.0))

        # Parse matched location
        matched_loc_data = result.get("matched_location", {})
        matched_location = None
        if matched_loc_data:
            matched_location = MatchedLocation(
                page_number=matched_loc_data.get("page_number"),
                section_heading=matched_loc_data.get("section_heading"),
                exact_quote=matched_loc_data.get("exact_quote", ""),
            )

        # Parse citation chain
        chain_data = result.get("citation_chain", {})
        citation_chain = None
        if chain_data:
            citation_chain = CitationChain(
                intermediate_source=chain_data.get("intermediate_source"),
                intermediate_ref_id=chain_data.get("intermediate_ref_id"),
                ultimate_source=chain_data.get("ultimate_source"),
                ultimate_source_type=chain_data.get("ultimate_source_type"),
            )

        # Determine matched source document name
        matched_doc_name = result.get("matched_source_document")
        matched_doc_id = None
        if matched_doc_name:
            for doc in source_docs:
                if doc.original_filename == matched_doc_name or doc.document_label == matched_doc_name:
                    matched_doc_id = doc.file_id
                    matched_doc_name = doc.document_label or doc.original_filename
                    break

        discrepancies = result.get("discrepancies", "")
        reasoning = result.get("reasoning", "")

        # Hallucination guard
        if matched_location and matched_location.exact_quote and status == VerificationStatus.VERIFIED:
            quote = matched_location.exact_quote.lower()
            found_in_chunks = any(
                quote[:50] in chunk["text"].lower()
                for chunk in relevant_chunks
                if len(quote) >= 50
            )
            if not found_in_chunks and len(quote) >= 50:
                status = VerificationStatus.PARTIALLY_VERIFIED
                discrepancies = (discrepancies or "") + " [SourceLens: Quote not found verbatim in source — possible LLM hallucination]"
                confidence = min(confidence, 0.6)

        return Verification(
            status=status,
            confidence_score=confidence,
            matched_source_document=matched_doc_id,
            matched_source_document_name=matched_doc_name,
            matched_location=matched_location,
            citation_chain=citation_chain,
            verification_notes=discrepancies or "",
            llm_reasoning=reasoning,
        )

    except Exception as e:
        logger.error(f"Verification failed for metric '{metric.extracted_metric.value}': {e}")
        return _default_verification(str(e))


def _default_verification(note: str) -> Verification:
    return Verification(
        status=VerificationStatus.NOT_FOUND,
        confidence_score=0.0,
        verification_notes=note,
        llm_reasoning=f"Verification could not be completed: {note}",
    )


def _generate_demo_verification(
    metric: MetricRecord,
    relevant_chunks: list[dict],
    source_docs: list[FileRef],
) -> Verification:
    """
    Generate realistic demo verification results.
    Uses text matching heuristics to create plausible results.
    """
    metric_value = metric.extracted_metric.value.lower()

    # Try to find the metric value in source chunks (real text matching)
    best_match = None
    best_score = 0.0
    for chunk in relevant_chunks:
        chunk_text = chunk["text"].lower()
        # Check if exact value appears in chunk
        if metric_value in chunk_text:
            best_match = chunk
            best_score = 0.95
            break
        # Check partial numeric match
        import re
        nums = re.findall(r'[\d,.]+', metric_value)
        for num in nums:
            if num in chunk_text and len(num) >= 2:
                if not best_match or 0.7 > best_score:
                    best_match = chunk
                    best_score = 0.7

    # Determine status based on match quality
    if best_score >= 0.9:
        status = VerificationStatus.VERIFIED
        confidence = random.uniform(0.85, 0.98)
    elif best_score >= 0.6:
        status = VerificationStatus.PARTIALLY_VERIFIED
        confidence = random.uniform(0.55, 0.75)
    elif relevant_chunks:
        # Some chunks found but no match
        status = random.choice([VerificationStatus.UNVERIFIED, VerificationStatus.NOT_FOUND])
        confidence = random.uniform(0.1, 0.4)
    else:
        status = VerificationStatus.NOT_FOUND
        confidence = 0.0

    # Build matched location from best chunk
    matched_location = None
    matched_doc_name = None
    matched_doc_id = None

    if best_match:
        meta = best_match.get("metadata", {})
        file_id = meta.get("source_file_id", "")

        for doc in source_docs:
            if doc.file_id == file_id:
                matched_doc_name = doc.document_label or doc.original_filename
                matched_doc_id = doc.file_id
                break

        # Extract a quote around the matched area
        chunk_text = best_match["text"]
        quote_start = chunk_text.lower().find(metric_value)
        if quote_start >= 0:
            qs = max(0, quote_start - 100)
            qe = min(len(chunk_text), quote_start + len(metric_value) + 100)
            exact_quote = chunk_text[qs:qe].strip()
        else:
            exact_quote = chunk_text[:250].strip()

        matched_location = MatchedLocation(
            page_number=int(meta.get("page_number", 0)) or None,
            section_heading=meta.get("section_heading") or None,
            exact_quote=exact_quote,
        )

    # Build demo citation chain
    ultimate_sources = [
        ("McKinsey & Company POBOS Study (2025)", "consultancy_publication"),
        ("ISPE Pharmaceutical Engineering Journal", "peer_reviewed"),
        ("FDA Guidance for Industry: Process Validation", "regulatory_document"),
        ("PDA Technical Report No. 60", "industry_report"),
        ("Deloitte Life Sciences Outlook 2025", "consultancy_publication"),
        ("ICH Q10: Pharmaceutical Quality System", "regulatory_document"),
        ("Benchmarking Pro Survey 2024", "industry_report"),
    ]

    ult_source, ult_type = random.choice(ultimate_sources)

    citation_chain = CitationChain(
        intermediate_source=matched_doc_name,
        intermediate_ref_id=f"[{random.randint(1, 28)}]" if matched_doc_name else None,
        ultimate_source=ult_source if status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED) else None,
        ultimate_source_type=ult_type if status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED) else None,
    )

    # Build demo reliability
    tier_map = {
        "peer_reviewed": (ReliabilityTier.TIER_1, "Gold Standard", 5),
        "regulatory_document": (ReliabilityTier.TIER_1, "Gold Standard", 5),
        "industry_report": (ReliabilityTier.TIER_2, "Established & Reputable", 4),
        "consultancy_publication": (ReliabilityTier.TIER_2, "Established & Reputable", 4),
    }
    tier_info = tier_map.get(ult_type, (ReliabilityTier.TIER_3, "Acceptable / Niche", 3))

    source_reliability = SourceReliability(
        tier=tier_info[0],
        tier_label=tier_info[1],
        stars=tier_info[2],
        reasoning=f"[DEMO] {ult_source} is classified as {tier_info[1]}.",
        recommendation="Verify source methodology and recency before final submission." if tier_info[2] < 5 else "Strong source — cite with confidence.",
    ) if status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED) else None

    reasoning_templates = {
        VerificationStatus.VERIFIED: f"[DEMO] The metric '{metric.extracted_metric.value}' was found in the source document with a direct numerical match.",
        VerificationStatus.PARTIALLY_VERIFIED: f"[DEMO] The metric '{metric.extracted_metric.value}' is directionally supported but the exact value differs slightly from the source.",
        VerificationStatus.UNVERIFIED: f"[DEMO] The metric '{metric.extracted_metric.value}' could not be located in any provided source document.",
        VerificationStatus.CONTRADICTED: f"[DEMO] The source document contains data that contradicts '{metric.extracted_metric.value}'.",
        VerificationStatus.NOT_FOUND: f"[DEMO] No relevant passages were found for this metric in the source documents.",
    }

    return Verification(
        status=status,
        confidence_score=round(confidence, 2),
        matched_source_document=matched_doc_id,
        matched_source_document_name=matched_doc_name,
        matched_location=matched_location,
        citation_chain=citation_chain,
        source_reliability=source_reliability,
        verification_notes="[Demo Mode] Results generated using text-matching heuristics",
        llm_reasoning=reasoning_templates.get(status, ""),
    )
