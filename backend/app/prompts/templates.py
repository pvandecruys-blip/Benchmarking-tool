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


VERIFICATION_PROMPT = """You are a pragmatic fact-checking auditor for a management consulting firm.
Your job: decide whether the SAME underlying fact appears in the source
excerpts, even if the slide formats or expresses it differently.

METRIC TO VERIFY:
- Value: {metric_value}
- Description: {metric_description}
- Full context from slide: {context_sentence}
- Source attribution on slide (if any): {slide_source_tag}

SOURCE DOCUMENT EXCERPTS (ranked by relevance):
{source_excerpts}

═══════════════════════════════════════════════════════════════════════════
CORE PRINCIPLE — READ THIS FIRST
═══════════════════════════════════════════════════════════════════════════
Consulting slides REFORMAT data from their sources. Your goal is to find the
underlying fact, NOT to demand verbatim numeric equality. Two expressions of
the same fact = VERIFIED, not partially_verified.

The following pairs are ALL fully VERIFIED matches (status = "verified"):
- Slide: "33%"                 Source: "one-third" / "a third of" / "~33%"
- Slide: "30-40%"              Source: "between 30 and 40 percent" / "33%" / "35%"
- Slide: "$8M-$12M"            Source: "approximately ten million dollars" / "around $10M"
- Slide: "90-131 days"         Source: "median closure time of 110 days" / "3-4 months"
- Slide: "reduced by 50%"      Source: "cut in half" / "halved" / "dropped from 200 to 100"
- Slide: "top quartile"        Source: "75th percentile performers" / "upper 25%"
- Slide: "208 sites"           Source: "over 200 sites" / "a global footprint of 208 facilities"
- Slide: "5-10 days → 1-3 days"  Source: a before/after reduction described in words
- Slide: "1/6th of median"     Source: "approximately 17%" / "roughly one-sixth"
- Slide rounds 34.7% → "~35%"  Source: "34.7%"   → VERIFIED (rounding is normal)

Only use PARTIALLY_VERIFIED when the source discusses the same topic/metric
type but the specific numeric claim cannot be reconciled even via rounding,
ranges, or unit conversion.

Only use CONTRADICTED when the source states a clearly different value for
the same metric (e.g., slide says "30%", source says "15%" — not a rounding
difference).

═══════════════════════════════════════════════════════════════════════════
VERIFICATION TASKS
═══════════════════════════════════════════════════════════════════════════

1. **MATCH ASSESSMENT** — Apply the principle above. Accept any of:
   - Exact numerical match
   - Equivalent fractions / decimals / percentages (one-third ↔ 33%)
   - Ranges that encompass a point value, or point values inside a range
   - Rounded, approximated, or truncated versions (±10% tolerance is fine)
   - Unit conversions (days ↔ months, $M ↔ million)
   - Before/after pairs described narratively
   - Aggregate totals (208 sites = 52 countries × average sites/country)

2. **EXACT QUOTE** — Copy the most relevant verbatim passage from the source.
   Must be a literal substring of one of the excerpts, not a paraphrase. If
   nothing matches, state "No supporting passage found."

3. **CITATION CHAIN** — If the source text itself cites an underlying source
   (e.g., "according to McKinsey POBOS [ref 1]", "data from MDIC [9]"):
   - intermediate_source: the document you're reading
   - intermediate_ref_id: the reference marker (e.g., "[9]")
   - ultimate_source: the original source cited
   - ultimate_source_type: categorize it

4. **DISCREPANCY CHECK** — Only flag actual problems:
   - Source states a genuinely different number (not just rounding)
   - Metric taken out of context (different population, different period)
   - Slide claims stronger evidence than the source supports

5. **VERIFICATION STATUS** — Be decisive. Default to VERIFIED when the
   underlying fact is present:
   - VERIFIED: Same underlying fact is in the source (even if formatted
     differently). This is the MOST COMMON outcome when sources are relevant.
   - PARTIALLY_VERIFIED: Source discusses the same metric type but specific
     value cannot be reconciled. Use sparingly.
   - UNVERIFIED: Source excerpts do not discuss this metric at all.
   - CONTRADICTED: Source clearly states a different value for the same
     metric (beyond rounding tolerance).
   - NOT_FOUND: Metric type absent from all excerpts.

6. **CONFIDENCE SCORE** — 0.0 to 1.0. Use ≥0.8 when you're clearly right,
   0.5-0.8 for good-but-not-certain matches, <0.5 when you're uncertain.

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
  "discrepancies": "string describing any real issues, or null",
  "reasoning": "2-4 sentences — state WHY the slide value and source passage describe the same fact (e.g., 'Source says one-third; slide rounds to 33%. Same fact.')"
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
