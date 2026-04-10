"""
SourceLens — PPTX Comment Annotator
Injects modern PowerPoint comments (Office 365 / 2021+ format) into PPTX files.

This module replicates the exact XML structure found in the reference PPTX file,
using the p188 (PowerPoint 2018/8) namespace for modern threaded comments.

Reference XML format (reverse-engineered from test file):
- Authors: ppt/authors.xml (p188:authorLst)
- Comments: ppt/comments/modernComment_{hash}_{N}.xml (p188:cmLst)
- Relationships: Microsoft 2018/10 relationship types
- Content Types: application/vnd.ms-powerpoint.{authors,comments}+xml
"""

import zipfile
import io
import os
import uuid
import hashlib
import re
from datetime import datetime
from lxml import etree
from collections import defaultdict
from app.models import MetricRecord, VerificationStatus, SlideRecord
import logging

logger = logging.getLogger(__name__)

# ─── Namespaces ───────────────────────────────────────────────────────────────

NS_P188 = "http://schemas.microsoft.com/office/powerpoint/2018/8/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_AC = "http://schemas.microsoft.com/office/drawing/2013/main/command"
NS_PC = "http://schemas.microsoft.com/office/powerpoint/2013/main/command"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

NSMAP_COMMENT = {"p188": NS_P188, "a": NS_A, "r": NS_R}
NSMAP_AC = {"ac": NS_AC}
NSMAP_PC = {"pc": NS_PC}

# Relationship type URIs (modern format)
RT_AUTHORS = "http://schemas.microsoft.com/office/2018/10/relationships/authors"
RT_COMMENTS = "http://schemas.microsoft.com/office/2018/10/relationships/comments"

# Content types
CT_AUTHORS = "application/vnd.ms-powerpoint.authors+xml"
CT_COMMENTS = "application/vnd.ms-powerpoint.comments+xml"

# Status emoji mapping
STATUS_EMOJI = {
    VerificationStatus.VERIFIED: "✅",
    VerificationStatus.PARTIALLY_VERIFIED: "⚠️",
    VerificationStatus.UNVERIFIED: "❌",
    VerificationStatus.CONTRADICTED: "🚫",
    VerificationStatus.NOT_FOUND: "❓",
}


def _make_guid() -> str:
    """Generate a GUID string in {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX} format."""
    return "{" + str(uuid.uuid4()).upper() + "}"


def _format_comment_text(metric: MetricRecord) -> str:
    """Format the audit trail comment text for a single metric."""
    v = metric.verification
    if not v:
        return f"[SourceLens Audit]\n\nMETRIC: {metric.extracted_metric.value} — {metric.extracted_metric.description}\nSTATUS: ❓ NOT ASSESSED"

    emoji = STATUS_EMOJI.get(v.status, "❓")
    confidence_pct = int(v.confidence_score * 100)

    lines = [
        f"[SourceLens Audit]",
        f"",
        f"METRIC: {metric.extracted_metric.value} — {metric.extracted_metric.description}",
        f"STATUS: {emoji} {v.status.value.upper()} (confidence: {confidence_pct}%)",
        f"",
    ]

    # Source trail
    if v.matched_location:
        loc = v.matched_location
        quote = loc.exact_quote[:250] + "..." if len(loc.exact_quote) > 250 else loc.exact_quote
        lines.append("SOURCE TRAIL:")
        lines.append(f"├─ Found in: {v.matched_source_document_name or 'Unknown'}")
        if loc.page_number:
            lines.append(f"│  Page: {loc.page_number}")
        if loc.section_heading:
            lines.append(f"│  Section: {loc.section_heading}")
        lines.append(f'│  Quote: "{quote}"')
        lines.append("│")

    if v.citation_chain:
        cc = v.citation_chain
        if cc.intermediate_ref_id:
            lines.append(f"├─ Reference: {cc.intermediate_ref_id} in {cc.intermediate_source or 'source'}")
            lines.append("│")
        if cc.ultimate_source:
            lines.append(f"└─ Original Source: {cc.ultimate_source}")
            if cc.ultimate_source_type:
                lines.append(f"   Type: {cc.ultimate_source_type}")

    if v.source_reliability:
        sr = v.source_reliability
        stars = "★" * sr.stars + "☆" * (5 - sr.stars)
        lines.append(f"   Reliability: {stars} {sr.tier.value} — {sr.tier_label}")

    # Discrepancies and recommendations
    if v.verification_notes:
        lines.append(f"\n⚠️ NOTE: {v.verification_notes}")
    if v.source_reliability and v.source_reliability.recommendation:
        lines.append(f"\n💡 RECOMMENDATION: {v.source_reliability.recommendation}")

    return "\n".join(lines)


def _format_grouped_comment(metrics: list[MetricRecord]) -> str:
    """Format multiple metrics into a single comment (when multiple metrics share a shape)."""
    if len(metrics) == 1:
        return _format_comment_text(metrics[0])

    parts = []
    for i, metric in enumerate(metrics):
        parts.append(_format_comment_text(metric))
        if i < len(metrics) - 1:
            parts.append("\n─── ─── ───\n")
    return "\n".join(parts)


def inject_comments(
    input_pptx_path: str,
    output_pptx_path: str,
    metrics: list[MetricRecord],
    slides: list[SlideRecord],
    author_name: str = "SourceLens Audit",
    initials: str = "SL",
) -> str:
    """
    Inject modern PowerPoint comments into a PPTX file.

    This works by:
    1. Reading the PPTX as a ZIP archive
    2. Creating/updating authors.xml with the SourceLens author
    3. Creating modernComment XML files for each slide with metrics
    4. Updating relationship files and [Content_Types].xml
    5. Writing the modified ZIP as the output PPTX

    Returns the path to the annotated PPTX file.
    """
    logger.info(f"Injecting comments into {input_pptx_path}")

    # Group metrics by slide number, then by shape_id
    slide_metrics: dict[int, dict[int, list[MetricRecord]]] = defaultdict(lambda: defaultdict(list))
    for metric in metrics:
        if metric.verification:  # Only comment on metrics that have been processed
            slide_metrics[metric.slide_number][metric.shape_id].append(metric)

    if not slide_metrics:
        logger.warning("No metrics with verification results to inject")
        # Just copy the file
        import shutil
        shutil.copy2(input_pptx_path, output_pptx_path)
        return output_pptx_path

    # Build slide_number → slide_id mapping
    slide_id_map = {}
    for slide in slides:
        slide_id_map[slide.slide_number] = slide.slide_id

    # Build shape position lookup: (slide_number, shape_id) → position
    shape_positions = {}
    for slide in slides:
        for shape in slide.shapes:
            shape_positions[(slide.slide_number, shape.shape_id)] = shape.position

    # Read the input PPTX
    input_buffer = io.BytesIO()
    with open(input_pptx_path, "rb") as f:
        input_buffer.write(f.read())
    input_buffer.seek(0)

    # Read all entries from the ZIP
    zip_contents = {}
    with zipfile.ZipFile(input_buffer, "r") as zin:
        for item in zin.namelist():
            zip_contents[item] = zin.read(item)

    # ─── Step 1: Create/Update Authors ────────────────────────────────────────
    author_id = _make_guid()
    authors_path = "ppt/authors.xml"

    if authors_path in zip_contents:
        # Parse existing authors and add SourceLens if not present
        authors_root = etree.fromstring(zip_contents[authors_path])
        # Check if SourceLens author already exists
        sl_exists = False
        for author_el in authors_root.findall(f"{{{NS_P188}}}author"):
            if author_el.get("name") == author_name:
                author_id = author_el.get("id")
                sl_exists = True
                break
        if not sl_exists:
            author_el = etree.SubElement(authors_root, f"{{{NS_P188}}}author")
            author_el.set("id", author_id)
            author_el.set("name", author_name)
            author_el.set("initials", initials)
            author_el.set("userId", f"sourcelens-{uuid.uuid4()}")
            author_el.set("providerId", "None")
        zip_contents[authors_path] = etree.tostring(
            authors_root, xml_declaration=True, encoding="UTF-8", standalone=True
        )
    else:
        # Create new authors file
        authors_root = etree.Element(
            f"{{{NS_P188}}}authorLst",
            nsmap={"p188": NS_P188, "a": NS_A, "r": NS_R}
        )
        author_el = etree.SubElement(authors_root, f"{{{NS_P188}}}author")
        author_el.set("id", author_id)
        author_el.set("name", author_name)
        author_el.set("initials", initials)
        author_el.set("userId", f"sourcelens-{uuid.uuid4()}")
        author_el.set("providerId", "None")
        zip_contents[authors_path] = etree.tostring(
            authors_root, xml_declaration=True, encoding="UTF-8", standalone=True
        )
        # Add authors relationship to presentation.rels
        _add_presentation_author_rel(zip_contents)

    # ─── Step 2: Create Comment Files for Each Slide ──────────────────────────
    comment_idx = 0
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")

    for slide_num, shape_groups in sorted(slide_metrics.items()):
        slide_id = slide_id_map.get(slide_num, 256 + slide_num)

        # Generate a hash for the comment filename (matching the reference file pattern)
        hash_base = f"sourcelens_{slide_num}_{comment_idx}"
        hash_hex = hashlib.md5(hash_base.encode()).hexdigest()[:8].upper()
        comment_filename = f"modernComment_{hash_hex}_{comment_idx}.xml"
        comment_path = f"ppt/comments/{comment_filename}"

        # Check if this slide already has a comments file
        slide_rels_path = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
        existing_comment_path = _find_existing_comment_path(zip_contents, slide_rels_path)

        if existing_comment_path:
            # Append to existing comment file
            comment_path = existing_comment_path
            cm_list_root = etree.fromstring(zip_contents[comment_path])
        else:
            # Create new comment list
            cm_list_root = etree.Element(
                f"{{{NS_P188}}}cmLst",
                nsmap={"p188": NS_P188, "a": NS_A, "r": NS_R}
            )

        # Add comments for each shape group
        cm_idx = len(cm_list_root.findall(f"{{{NS_P188}}}cm")) + 1

        for shape_id, shape_metrics in shape_groups.items():
            comment_text = _format_grouped_comment(shape_metrics)

            # Get position — center-top of the shape
            pos = shape_positions.get((slide_num, shape_id))
            if pos:
                x = pos.left + (pos.width // 2)
                y = pos.top
            else:
                x = 4572000  # Default center of slide
                y = 1000000

            # Create the comment element
            cm_el = etree.SubElement(cm_list_root, f"{{{NS_P188}}}cm")
            cm_el.set("id", _make_guid())
            cm_el.set("authorId", author_id)
            cm_el.set("created", now_str)

            # Add text marker list (anchoring to shape)
            txmk_list = etree.SubElement(cm_el, f"{{{NS_AC}}}txMkLst", nsmap={"ac": NS_AC})
            etree.SubElement(txmk_list, f"{{{NS_PC}}}docMk", nsmap={"pc": NS_PC})
            sld_mk = etree.SubElement(txmk_list, f"{{{NS_PC}}}sldMk", nsmap={"pc": NS_PC})
            sld_mk.set("cId", "0")
            sld_mk.set("sldId", str(slide_id))
            sp_mk = etree.SubElement(txmk_list, f"{{{NS_AC}}}spMk")
            sp_mk.set("id", str(shape_id))
            sp_mk.set("creationId", "{00000000-0000-0000-0000-000000000000}")

            # Position element
            pos_el = etree.SubElement(cm_el, f"{{{NS_P188}}}pos")
            pos_el.set("x", str(x))
            pos_el.set("y", str(y))

            # Comment text body
            tx_body = etree.SubElement(cm_el, f"{{{NS_P188}}}txBody")
            etree.SubElement(tx_body, f"{{{NS_A}}}bodyPr")
            etree.SubElement(tx_body, f"{{{NS_A}}}lstStyle")

            # Split comment text into paragraphs
            for para_text in comment_text.split("\n"):
                p_el = etree.SubElement(tx_body, f"{{{NS_A}}}p")
                r_el = etree.SubElement(p_el, f"{{{NS_A}}}r")
                rpr_el = etree.SubElement(r_el, f"{{{NS_A}}}rPr")
                rpr_el.set("lang", "en-GB")
                t_el = etree.SubElement(r_el, f"{{{NS_A}}}t")
                t_el.text = para_text

            cm_idx += 1

        # Write the comment file
        zip_contents[comment_path] = etree.tostring(
            cm_list_root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

        # Update slide relationships if this is a new comment file
        if not existing_comment_path:
            _add_slide_comment_rel(zip_contents, slide_num, comment_filename)

        # Update content types
        _ensure_content_type(zip_contents, comment_path)

        comment_idx += 1
        logger.info(f"Injected {len(shape_groups)} comment(s) on slide {slide_num}")

    # Ensure authors content type is registered
    _ensure_content_type_authors(zip_contents)

    # ─── Step 3: Write Output PPTX ───────────────────────────────────────────
    output_buffer = io.BytesIO()
    with zipfile.ZipFile(output_buffer, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in zip_contents.items():
            zout.writestr(name, data)

    with open(output_pptx_path, "wb") as f:
        f.write(output_buffer.getvalue())

    logger.info(f"Annotated PPTX saved to {output_pptx_path}")
    return output_pptx_path


def _find_existing_comment_path(zip_contents: dict, slide_rels_path: str) -> str | None:
    """Check if a slide already has a modern comments relationship."""
    if slide_rels_path not in zip_contents:
        return None

    rels_xml = etree.fromstring(zip_contents[slide_rels_path])
    for rel in rels_xml.findall(f"{{{NS_REL}}}Relationship"):
        rel_type = rel.get("Type", "")
        if "relationships/comments" in rel_type:
            target = rel.get("Target", "")
            # Resolve relative path
            if target.startswith("../"):
                return "ppt/" + target[3:]
            return target
    return None


def _add_presentation_author_rel(zip_contents: dict):
    """Add the authors relationship to the presentation .rels file."""
    pres_rels_path = "ppt/_rels/presentation.xml.rels"
    if pres_rels_path in zip_contents:
        rels_root = etree.fromstring(zip_contents[pres_rels_path])
    else:
        rels_root = etree.Element(f"{{{NS_REL}}}Relationships", nsmap={None: NS_REL})

    # Check if authors rel already exists
    for rel in rels_root.findall(f"{{{NS_REL}}}Relationship"):
        if "authors" in rel.get("Type", ""):
            return  # Already exists

    # Find next rId
    existing_ids = []
    for rel in rels_root.findall(f"{{{NS_REL}}}Relationship"):
        rid = rel.get("Id", "")
        m = re.search(r"(\d+)", rid)
        if m:
            existing_ids.append(int(m.group(1)))
    next_id = max(existing_ids) + 1 if existing_ids else 1

    rel_el = etree.SubElement(rels_root, f"{{{NS_REL}}}Relationship")
    rel_el.set("Id", f"rId{next_id}")
    rel_el.set("Type", RT_AUTHORS)
    rel_el.set("Target", "authors.xml")

    zip_contents[pres_rels_path] = etree.tostring(
        rels_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def _add_slide_comment_rel(zip_contents: dict, slide_num: int, comment_filename: str):
    """Add a comment relationship to a slide's .rels file."""
    rels_path = f"ppt/slides/_rels/slide{slide_num}.xml.rels"

    if rels_path in zip_contents:
        rels_root = etree.fromstring(zip_contents[rels_path])
    else:
        rels_root = etree.Element(f"{{{NS_REL}}}Relationships", nsmap={None: NS_REL})

    # Find next rId
    existing_ids = []
    for rel in rels_root.findall(f"{{{NS_REL}}}Relationship"):
        rid = rel.get("Id", "")
        m = re.search(r"(\d+)", rid)
        if m:
            existing_ids.append(int(m.group(1)))
    next_id = max(existing_ids) + 1 if existing_ids else 1

    rel_el = etree.SubElement(rels_root, f"{{{NS_REL}}}Relationship")
    rel_el.set("Id", f"rId{next_id}")
    rel_el.set("Type", RT_COMMENTS)
    rel_el.set("Target", f"../comments/{comment_filename}")

    zip_contents[rels_path] = etree.tostring(
        rels_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def _ensure_content_type(zip_contents: dict, comment_path: str):
    """Ensure the [Content_Types].xml has an entry for this comment file."""
    ct_path = "[Content_Types].xml"
    ct_root = etree.fromstring(zip_contents[ct_path])

    part_name = "/" + comment_path

    # Check if already registered
    for override in ct_root.findall(f"{{{NS_CT}}}Override"):
        if override.get("PartName") == part_name:
            return

    override_el = etree.SubElement(ct_root, f"{{{NS_CT}}}Override")
    override_el.set("PartName", part_name)
    override_el.set("ContentType", CT_COMMENTS)

    zip_contents[ct_path] = etree.tostring(
        ct_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


def _ensure_content_type_authors(zip_contents: dict):
    """Ensure the [Content_Types].xml has an entry for authors.xml."""
    ct_path = "[Content_Types].xml"
    ct_root = etree.fromstring(zip_contents[ct_path])

    part_name = "/ppt/authors.xml"

    for override in ct_root.findall(f"{{{NS_CT}}}Override"):
        if override.get("PartName") == part_name:
            return

    override_el = etree.SubElement(ct_root, f"{{{NS_CT}}}Override")
    override_el.set("PartName", part_name)
    override_el.set("ContentType", CT_AUTHORS)

    zip_contents[ct_path] = etree.tostring(
        ct_root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
