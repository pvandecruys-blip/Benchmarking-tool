"""
SourceLens — LLM Prompt Templates
All prompts used for metric extraction, verification, and source assessment.
"""

METRIC_EXTRACTION_PROMPT = """You are a precision data extraction system for consulting presentations. Your
task is to extract EVERY quantitative metric, benchmark, data point,
statistical claim, and specific factual assertion from the following slide
content.

SLIDE {slide_number}: "{slide_title}"
SLIDE CONTENT:
{slide_content}

EXTRACTION RULES:
1. Extract ALL numbers, percentages, currency amounts, durations, ratios,
   and ranges
2. Extract qualitative benchmarks that imply specific performance levels
   (e.g., "top quartile", "best-in-class", "industry average")
3. For each metric, identify WHICH shape/textbox it appears in (using the
   shape IDs provided)
4. Capture the full sentence context around each metric
5. If the slide contains a source tag or attribution line (usually at the
   bottom in small text), capture it separately as "slide_source_tag"
6. DO NOT extract:
   - Page numbers
   - Dates that are just timestamps (e.g., "April 2026")
   - Generic labels without quantitative meaning (e.g., "Phase 1", "Step 3")
   - Branding text

For each metric found, return:
{{
  "shape_id": "the shape ID where this metric appears",
  "value": "the exact metric value as written (e.g., '90-131 days', '30-40%',
            '$8M-$12M')",
  "metric_type": "percentage | currency | duration | ratio | count | range |
                  qualitative_benchmark",
  "description": "brief description of what this metric represents",
  "context_sentence": "the full sentence containing this metric",
  "slide_source_tag": "any source attribution text found on this slide, or null"
}}

Return as a JSON array. Be exhaustive — miss nothing.
If no metrics are found on this slide, return an empty array: []"""


VERIFICATION_PROMPT = """You are a meticulous fact-checking auditor for a management consulting firm.
Your task is to verify whether a specific metric from a client presentation is
supported by the provided source document excerpts.

METRIC TO VERIFY:
- Value: {metric_value}
- Description: {metric_description}
- Full context from slide: {context_sentence}
- Source attribution on slide (if any): {slide_source_tag}

SOURCE DOCUMENT EXCERPTS (ranked by relevance):
{source_excerpts}

VERIFICATION TASKS:

1. **MATCH ASSESSMENT**: Does any source excerpt contain or directly support
   this exact metric value? Consider:
   - Exact numerical match
   - Equivalent expressions (e.g., "one-sixth" = "1/6th" = "~83% reduction")
   - Ranges that encompass the stated value
   - Rounded or aggregated versions of the same data

2. **EXACT QUOTE**: Copy the most relevant verbatim passage from the source
   that supports (or contradicts) this metric. If no match, state "No
   supporting passage found."

3. **CITATION CHAIN**: If the source document itself cites an underlying
   source for this metric (e.g., the text says "according to McKinsey POBOS
   [ref 1]" or "data from MDIC pilot study [9]"):
   - Identify the intermediate source (the document you're reading)
   - Identify the reference ID used (e.g., "[9]", "ref [1]")
   - Identify the ultimate/original source being cited

4. **DISCREPANCY CHECK**: Is the metric on the slide an accurate
   representation of what the source says? Flag if:
   - The number has been rounded or approximated beyond reasonable tolerance
   - The metric has been taken out of context
   - The source actually states something different

5. **VERIFICATION STATUS**: Assign one of:
   - VERIFIED: Exact or near-exact match found in source with clear support
   - PARTIALLY_VERIFIED: The metric is directionally supported but not
     precisely matched
   - UNVERIFIED: Cannot find this metric in any provided source document
   - CONTRADICTED: Source document contains data that contradicts this metric
   - NOT_FOUND: The metric type is present in sources but the specific value
     cannot be located

6. **CONFIDENCE SCORE**: 0.0 to 1.0 reflecting your confidence in the
   verification

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "status": "verified | partially_verified | unverified | contradicted | not_found",
  "confidence_score": 0.85,
  "matched_source_document": "filename or null",
  "matched_location": {{
    "page_number": null,
    "section_heading": "string or null",
    "exact_quote": "verbatim supporting text from source"
  }},
  "citation_chain": {{
    "intermediate_source": "the document where the data was found",
    "intermediate_ref_id": "reference number used in that document or null",
    "ultimate_source": "the original source cited or null",
    "ultimate_source_type": "peer_reviewed | industry_report | consultancy_publication | regulatory_document | news_article | conference_paper | company_publication | unknown"
  }},
  "discrepancies": "string describing any issues, or null",
  "reasoning": "2-4 sentence explanation of your verification logic"
}}"""


BIBLIOGRAPHY_EXTRACTION_PROMPT = """You are a citation parser. Given the following bibliography/reference section
from a research document, extract each reference into a structured format.

For each reference, provide:
- ref_id: The reference number or identifier as it appears (e.g., "[1]", "[28]")
- full_text: The complete citation text
- authors: Author name(s) if present
- title: Title of the work
- publication: Journal, publisher, or platform name
- year: Publication year
- url: URL or DOI if present
- source_type: One of [peer_reviewed, industry_report, consultancy_publication,
  regulatory_document, news_article, conference_paper, company_publication,
  unknown]

Return ONLY valid JSON array (no markdown, no code blocks).

BIBLIOGRAPHY TEXT:
{bibliography_text}"""


RELIABILITY_ASSESSMENT_PROMPT = """You are an expert in evaluating the credibility and reliability of sources used
in pharmaceutical/life sciences industry benchmarking.

Assess the following source:
- Source Name: {source_name}
- Source Type: {source_type}
- Context: This source is cited as the origin for a benchmarking metric used
  in a consulting presentation.

RELIABILITY TIER CRITERIA:

**Tier 1 - Gold Standard** (Stars: 5)
Peer-reviewed journals, major regulatory body publications (FDA, EMA, ICH),
large-scale validated industry benchmarking programmes, ISO/ICH/ISPE standards.

**Tier 2 - Established & Reputable** (Stars: 4)
Major consulting firm publications (McKinsey, BCG, PwC), established industry
bodies (ISPE, PDA, MDIC), well-known conferences, government data.

**Tier 3 - Acceptable / Niche** (Stars: 3)
Niche publications, smaller consulting whitepapers, company case studies,
conference presentations, smaller surveys.

**Tier 4 - Caution / Unverifiable** (Stars: 2)
Blog posts, unclear methodology, self-reported data, AI-generated content
without citations, outdated sources.

**Unknown** (Stars: 1)
Cannot determine provenance.

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "tier": "Tier 1 | Tier 2 | Tier 3 | Tier 4 | Unknown",
  "tier_label": "Gold Standard | Established & Reputable | Acceptable / Niche | Caution / Unverifiable | Unknown",
  "stars": 5,
  "reasoning": "1-2 sentence justification",
  "recommendation": "action the consultant should take"
}}"""
