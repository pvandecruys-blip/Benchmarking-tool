"""
SourceLens — Source Reliability Assessor
Uses LLM to evaluate the credibility of ultimate source citations.
"""

import json
import logging
from app.models import SourceReliability, ReliabilityTier, CitationChain
from app.prompts.templates import RELIABILITY_ASSESSMENT_PROMPT
from app.services.llm_client import llm_generate, parse_json_response, has_api_key
from app.config import get_settings

logger = logging.getLogger(__name__)


async def assess_reliability(citation_chain: CitationChain) -> SourceReliability:
    """
    Assess the reliability of the ultimate source in a citation chain.
    """
    if not citation_chain or not citation_chain.ultimate_source:
        return SourceReliability(
            tier=ReliabilityTier.UNKNOWN,
            tier_label="Unknown",
            stars=1,
            reasoning="No ultimate source identified to assess.",
            recommendation="Identify and verify the original source for this metric.",
        )

    settings = get_settings()
    if not has_api_key() or settings.demo_mode:
        return _heuristic_assessment(citation_chain)

    prompt = RELIABILITY_ASSESSMENT_PROMPT.format(
        source_name=citation_chain.ultimate_source,
        source_type=citation_chain.ultimate_source_type or "unknown",
    )

    try:
        text = await llm_generate(
            prompt=prompt,
            system_prompt="You are a source reliability assessor. Respond with valid JSON only.",
            temperature=0.1,
            max_tokens=1024,
        )

        data = parse_json_response(text)
        if not isinstance(data, dict):
            return _heuristic_assessment(citation_chain)

        tier_str = data.get("tier", "Unknown")
        try:
            tier = ReliabilityTier(tier_str)
        except ValueError:
            tier = ReliabilityTier.UNKNOWN

        return SourceReliability(
            tier=tier,
            tier_label=data.get("tier_label", "Unknown"),
            stars=int(data.get("stars", 1)),
            reasoning=data.get("reasoning", ""),
            recommendation=data.get("recommendation", ""),
        )

    except Exception as e:
        logger.error(f"Reliability assessment failed: {e}")
        return _heuristic_assessment(citation_chain)


def _heuristic_assessment(chain: CitationChain) -> SourceReliability:
    """Simple heuristic assessment when LLM is unavailable."""
    source = (chain.ultimate_source or "").lower()
    source_type = (chain.ultimate_source_type or "").lower()

    # Tier 1 keywords
    tier1 = ["fda", "ema", "ich", "iso", "nature", "science", "lancet", "nejm", "peer-reviewed"]
    # Tier 2 keywords
    tier2 = ["mckinsey", "bcg", "deloitte", "pwc", "ey", "kpmg", "ispe", "pda", "mdic", "gartner"]
    # Tier 3 keywords
    tier3 = ["conference", "whitepaper", "case study", "survey"]

    for kw in tier1:
        if kw in source or kw in source_type:
            return SourceReliability(
                tier=ReliabilityTier.TIER_1, tier_label="Gold Standard", stars=5,
                reasoning=f"Source appears to be a gold-standard reference ({kw}).",
                recommendation="Strong source — cite with confidence.",
            )

    for kw in tier2:
        if kw in source or kw in source_type:
            return SourceReliability(
                tier=ReliabilityTier.TIER_2, tier_label="Established & Reputable", stars=4,
                reasoning=f"Source is from an established, reputable organization ({kw}).",
                recommendation="Reliable source — consider citing methodology specifics.",
            )

    if source_type == "peer_reviewed":
        return SourceReliability(
            tier=ReliabilityTier.TIER_1, tier_label="Gold Standard", stars=5,
            reasoning="Peer-reviewed source.", recommendation="Strong source.",
        )

    if source_type in ("industry_report", "consultancy_publication"):
        return SourceReliability(
            tier=ReliabilityTier.TIER_2, tier_label="Established & Reputable", stars=4,
            reasoning="Industry/consultancy report.", recommendation="Verify methodology if possible.",
        )

    return SourceReliability(
        tier=ReliabilityTier.TIER_3, tier_label="Acceptable / Niche", stars=3,
        reasoning="Source credibility could not be fully assessed without LLM.",
        recommendation="Manually verify this source's credibility.",
    )
