"""
SourceLens — Metric Extractor
Uses LLM to extract metrics, data points, and benchmarks from slide content.
Supports demo mode with realistic mock data.
"""

import json
import random
import logging
from app.models import MetricRecord, ExtractedMetric, MetricType, SlideRecord
from app.prompts.templates import METRIC_EXTRACTION_PROMPT
from app.services.llm_client import llm_generate, parse_json_response, has_api_key
from app.config import get_settings

logger = logging.getLogger(__name__)


async def extract_metrics_from_slide(slide: SlideRecord) -> list[MetricRecord]:
    """
    Extract all metrics from a single slide using LLM.
    Falls back to demo mode if no API key is configured.
    """
    if not slide.all_text.strip():
        return []

    settings = get_settings()

    # Demo mode: generate realistic mock metrics from slide text
    if settings.demo_mode or not has_api_key():
        return _generate_demo_metrics(slide)

    # Build slide content with shape IDs
    shape_content_parts = []
    for shape in slide.shapes:
        if shape.text:
            shape_content_parts.append(f"[Shape ID: {shape.shape_id}, Name: {shape.shape_name}]\n{shape.text}")
        if shape.table:
            table_str = "\n".join(" | ".join(row) for row in shape.table)
            shape_content_parts.append(f"[Shape ID: {shape.shape_id}, Name: {shape.shape_name} (Table)]\n{table_str}")

    slide_content = "\n\n---\n\n".join(shape_content_parts)

    prompt = METRIC_EXTRACTION_PROMPT.format(
        slide_number=slide.slide_number,
        slide_title=slide.slide_title or "Untitled",
        slide_content=slide_content,
    )

    try:
        response_text = await llm_generate(
            prompt=prompt,
            system_prompt="You are a precision data extraction system. Always respond with valid JSON only, no markdown formatting.",
            temperature=0.1,
        )
        metrics_data = parse_json_response(response_text)

        if not isinstance(metrics_data, list):
            # Some models return {"metrics": [...]} — handle both
            if isinstance(metrics_data, dict) and "metrics" in metrics_data:
                metrics_data = metrics_data["metrics"]
            else:
                logger.warning(f"Slide {slide.slide_number}: LLM returned non-array response")
                return []

        records = []
        for item in metrics_data:
            try:
                shape_id = int(item.get("shape_id", 0))
                metric_type_str = item.get("metric_type", "percentage")

                try:
                    metric_type = MetricType(metric_type_str)
                except ValueError:
                    metric_type = MetricType.PERCENTAGE

                shape_text = ""
                for shape in slide.shapes:
                    if shape.shape_id == shape_id:
                        shape_text = shape.text
                        break

                record = MetricRecord(
                    slide_number=slide.slide_number,
                    slide_title=slide.slide_title,
                    shape_id=shape_id,
                    shape_text_context=shape_text,
                    extracted_metric=ExtractedMetric(
                        value=item.get("value", ""),
                        metric_type=metric_type,
                        description=item.get("description", ""),
                        context_sentence=item.get("context_sentence", ""),
                    ),
                    slide_source_tag=item.get("slide_source_tag"),
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse metric: {e}")
                continue

        logger.info(f"Slide {slide.slide_number}: extracted {len(records)} metrics")
        return records

    except Exception as e:
        logger.error(f"Metric extraction failed for slide {slide.slide_number}: {e}")
        return []


def _generate_demo_metrics(slide: SlideRecord) -> list[MetricRecord]:
    """
    Generate realistic demo metrics by scanning slide text for numbers/percentages.
    This creates believable data for demo purposes without an API key.
    """
    import re

    text = slide.all_text
    records = []

    # Find percentages
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*%', text):
        pct = m.group(0)
        # Get surrounding context (up to 100 chars before and after)
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 80)
        context = text[start:end].strip()

        shape_id = slide.shapes[0].shape_id if slide.shapes else 0
        # Try to find which shape contains this text
        for shape in slide.shapes:
            if pct in shape.text:
                shape_id = shape.shape_id
                break

        records.append(MetricRecord(
            slide_number=slide.slide_number,
            slide_title=slide.slide_title,
            shape_id=shape_id,
            shape_text_context=context,
            extracted_metric=ExtractedMetric(
                value=pct,
                metric_type=MetricType.PERCENTAGE,
                description=f"Percentage metric from slide {slide.slide_number}",
                context_sentence=context,
            ),
        ))

    # Find currency amounts
    for m in re.finditer(r'[\$€£]\s*[\d,.]+(?:\s*[MBKmk])?', text):
        val = m.group(0)
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 80)
        context = text[start:end].strip()

        shape_id = slide.shapes[0].shape_id if slide.shapes else 0
        for shape in slide.shapes:
            if val in shape.text:
                shape_id = shape.shape_id
                break

        records.append(MetricRecord(
            slide_number=slide.slide_number,
            slide_title=slide.slide_title,
            shape_id=shape_id,
            shape_text_context=context,
            extracted_metric=ExtractedMetric(
                value=val,
                metric_type=MetricType.CURRENCY,
                description=f"Currency metric from slide {slide.slide_number}",
                context_sentence=context,
            ),
        ))

    # Find duration/ranges (e.g., "90-131 days", "30-40 days")
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(days?|months?|weeks?|years?|hours?)', text, re.IGNORECASE):
        val = m.group(0)
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 80)
        context = text[start:end].strip()

        shape_id = slide.shapes[0].shape_id if slide.shapes else 0
        for shape in slide.shapes:
            if val in shape.text:
                shape_id = shape.shape_id
                break

        records.append(MetricRecord(
            slide_number=slide.slide_number,
            slide_title=slide.slide_title,
            shape_id=shape_id,
            shape_text_context=context,
            extracted_metric=ExtractedMetric(
                value=val,
                metric_type=MetricType.DURATION,
                description=f"Duration/range metric from slide {slide.slide_number}",
                context_sentence=context,
            ),
        ))

    # Find standalone numbers with qualitative context
    for m in re.finditer(r'(?:top|bottom|best|worst|average|median|quartile|benchmark)\s+(?:\w+\s+){0,3}(\d+(?:\.\d+)?)', text, re.IGNORECASE):
        val = m.group(0)
        start = max(0, m.start() - 60)
        end = min(len(text), m.end() + 60)
        context = text[start:end].strip()

        shape_id = slide.shapes[0].shape_id if slide.shapes else 0
        for shape in slide.shapes:
            if m.group(0) in shape.text:
                shape_id = shape.shape_id
                break

        records.append(MetricRecord(
            slide_number=slide.slide_number,
            slide_title=slide.slide_title,
            shape_id=shape_id,
            shape_text_context=context,
            extracted_metric=ExtractedMetric(
                value=val,
                metric_type=MetricType.QUALITATIVE_BENCHMARK,
                description=f"Benchmark reference from slide {slide.slide_number}",
                context_sentence=context,
            ),
        ))

    if records:
        logger.info(f"[DEMO] Slide {slide.slide_number}: extracted {len(records)} metrics via regex")
    return records
