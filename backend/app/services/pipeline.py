"""
SourceLens — Analysis Pipeline Orchestrator
Coordinates the three-phase analysis: Parse & Extract → Verify & Match → Annotate & Report.
"""

import os
import logging
from datetime import datetime
from app.models import (
    Project, ProjectStatus, FileRef, FileType, MetricRecord,
    AuditSummary, VerificationStatus
)
from app.config import get_settings
from app.services.pptx_parser import parse_pptx
from app.services.document_parser import parse_document
from app.services.bibliography import extract_bibliography
from app.services.chunker import chunk_document
from app.services.vector_store import get_vector_store, hybrid_rerank
from app.services.metric_extractor import extract_metrics_from_slide
from app.services.verifier import verify_metric
from app.services.citation_tracer import trace_citation_chain
from app.services.reliability import assess_reliability
from app.services.pptx_annotator import inject_comments
from app.services.excel_report import generate_excel_report

logger = logging.getLogger(__name__)

# In-memory project store
_projects: dict[str, Project] = {}


def get_project(project_id: str) -> Project | None:
    return _projects.get(project_id)


def get_all_projects() -> list[Project]:
    return list(_projects.values())


def save_project(project: Project):
    _projects[project.project_id] = project


def delete_project(project_id: str):
    _projects.pop(project_id, None)


def _log(project: Project, message: str, emoji: str = "ℹ️"):
    """Add a log entry to the project's processing log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "message": message,
        "emoji": emoji,
    }
    project.processing_log.append(entry)
    save_project(project)
    logger.info(f"[{project.project_id[:8]}] {message}")


async def run_analysis_pipeline(project_id: str):
    """
    Main analysis pipeline — runs all three phases sequentially.
    Updates project status and progress throughout.
    """
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    try:
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: PARSE & EXTRACT
        # ═══════════════════════════════════════════════════════════════════
        project.status = ProjectStatus.PHASE1
        project.current_phase = "Phase 1: Parse & Extract"
        project.progress_pct = 0
        project.progress_message = "Parsing presentation..."
        save_project(project)

        # 1a. Parse PPTX
        _log(project, "Parsing presentation slides...", "📊")
        pptx_path = project.presentation_file.file_path
        slides = parse_pptx(pptx_path)
        project.slides = slides
        project.presentation_file.page_count = len(slides)
        project.progress_pct = 15
        project.progress_message = f"Parsed {len(slides)} slides"
        _log(project, f"Found {len(slides)} slides", "✅")
        save_project(project)

        # 1b. Parse source documents
        _log(project, f"Parsing {len(project.source_documents)} source documents...", "📄")
        all_chunks = []
        for doc in project.source_documents:
            try:
                result = parse_document(doc.file_path, doc.file_type)
                doc.page_count = result["page_count"]

                # 1c. Extract bibliography
                bib_entries = await extract_bibliography(result["text"])
                doc.bibliography_entries = bib_entries
                doc.has_bibliography = len(bib_entries) > 0
                if bib_entries:
                    _log(project, f"Found {len(bib_entries)} references in {doc.document_label or doc.original_filename}", "📚")

                # 1d. Chunk document
                chunks = chunk_document(
                    result["text"],
                    doc.file_id,
                    result.get("pages"),
                )
                doc.chunk_count = len(chunks)
                all_chunks.extend(chunks)
                _log(project, f"Parsed {doc.document_label or doc.original_filename}: {doc.page_count} pages, {len(chunks)} chunks", "✅")
            except Exception as e:
                _log(project, f"Error parsing {doc.original_filename}: {str(e)}", "❌")

        project.progress_pct = 40
        project.progress_message = f"Building vector index ({len(all_chunks)} chunks)..."
        save_project(project)

        # 1e. Embed and store chunks
        _log(project, f"Building vector index from {len(all_chunks)} chunks...", "🔍")
        store = get_vector_store()
        store.create_collection(project.project_id)
        if all_chunks:
            store.add_chunks(all_chunks)
        _log(project, f"Vector index built with {len(all_chunks)} chunks", "✅")

        project.progress_pct = 60
        project.progress_message = "Extracting metrics from slides..."
        save_project(project)

        # 1f. Extract metrics from slides
        _log(project, "Extracting metrics from slides...", "🔢")
        all_metrics: list[MetricRecord] = []
        content_slides = [s for s in slides if not s.excluded and s.all_text.strip()]

        for slide in content_slides:
            metrics = await extract_metrics_from_slide(slide)
            all_metrics.extend(metrics)
            if metrics:
                _log(project, f"Slide {slide.slide_number}: extracted {len(metrics)} metrics", "📈")

        project.metrics = all_metrics
        project.progress_pct = 100
        project.progress_message = f"Phase 1 complete: {len(all_metrics)} metrics from {len(content_slides)} slides"
        _log(project, f"Extraction complete: {len(all_metrics)} metrics found", "✅")
        save_project(project)

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: VERIFY & MATCH
        # ═══════════════════════════════════════════════════════════════════
        project.status = ProjectStatus.PHASE2
        project.current_phase = "Phase 2: Verify & Match"
        project.progress_pct = 0
        project.progress_message = "Verifying metrics..."
        save_project(project)

        _log(project, f"Starting verification of {len(all_metrics)} metrics...", "🔍")

        for i, metric in enumerate(all_metrics):
            # 2a. Hybrid retrieval: vector search + keyword boost on numeric
            # tokens from the metric. Overfetch from the vector store, then
            # re-rank so chunks that literally contain the metric's numbers
            # surface above pure semantic matches that miss the figure.
            cfg = get_settings()
            top_k = cfg.max_chunks_per_query
            overfetch = max(top_k * cfg.retrieval_overfetch_factor, top_k)

            query = (
                f"{metric.extracted_metric.description} "
                f"{metric.extracted_metric.value} "
                f"{metric.extracted_metric.context_sentence}"
            )
            raw_chunks = store.query(query, n_results=overfetch)
            relevant_chunks = hybrid_rerank(
                raw_chunks,
                metric_value=metric.extracted_metric.value,
                metric_description=metric.extracted_metric.description,
                context_sentence=metric.extracted_metric.context_sentence,
                n_results=top_k,
            )

            # 2b. LLM verification
            verification = await verify_metric(metric, relevant_chunks, project.source_documents)
            metric.verification = verification

            # 2c. Citation chain tracing
            if verification.matched_source_document:
                matched_doc = None
                for doc in project.source_documents:
                    if doc.file_id == verification.matched_source_document:
                        matched_doc = doc
                        break
                if matched_doc and verification.matched_location:
                    chain = trace_citation_chain(
                        verification.matched_location.exact_quote or "",
                        matched_doc,
                        verification.citation_chain,
                    )
                    verification.citation_chain = chain

                    # 2d. Source reliability assessment
                    if chain and chain.ultimate_source:
                        reliability = await assess_reliability(chain)
                        verification.source_reliability = reliability

            # Update progress
            emoji = {
                VerificationStatus.VERIFIED: "✅",
                VerificationStatus.PARTIALLY_VERIFIED: "⚠️",
                VerificationStatus.UNVERIFIED: "❌",
                VerificationStatus.CONTRADICTED: "🚫",
                VerificationStatus.NOT_FOUND: "❓",
            }.get(verification.status, "❓")

            _log(project, f"Slide {metric.slide_number}: \"{metric.extracted_metric.value}\" → {verification.status.value.upper()}", emoji)

            progress = int((i + 1) / len(all_metrics) * 100)
            project.progress_pct = progress
            project.progress_message = f"Verified {i + 1}/{len(all_metrics)} metrics"
            save_project(project)

        _log(project, "Verification complete", "✅")

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 3: ANNOTATE & REPORT
        # ═══════════════════════════════════════════════════════════════════
        project.status = ProjectStatus.PHASE3
        project.current_phase = "Phase 3: Annotate & Report"
        project.progress_pct = 0
        project.progress_message = "Generating annotated PPTX..."
        save_project(project)

        # 3a. Inject comments into PPTX
        _log(project, "Injecting audit comments into presentation...", "💬")
        settings = get_settings()
        output_dir = os.path.join(settings.data_dir, "outputs", project.project_id)
        os.makedirs(output_dir, exist_ok=True)

        output_pptx_name = f"AUDITED_{project.presentation_file.original_filename}"
        output_pptx_path = os.path.join(output_dir, output_pptx_name)

        inject_comments(
            input_pptx_path=project.presentation_file.file_path,
            output_pptx_path=output_pptx_path,
            metrics=all_metrics,
            slides=slides,
        )
        project.annotated_pptx_path = output_pptx_path
        project.progress_pct = 40
        _log(project, "Annotated PPTX generated", "✅")
        save_project(project)

        # 3b. Generate Excel report
        _log(project, "Generating Excel audit report...", "📋")
        project.progress_message = "Generating Excel report..."
        excel_path = os.path.join(output_dir, f"SourceLens_Audit_{project.project_name}.xlsx")
        generate_excel_report(project, all_metrics, excel_path)
        project.excel_report_path = excel_path
        project.progress_pct = 70
        _log(project, "Excel report generated", "✅")
        save_project(project)

        # 3c. Compute summary stats
        _log(project, "Computing audit summary...", "📊")
        summary = _compute_summary(all_metrics, project.source_documents)
        project.summary_stats = summary
        project.progress_pct = 100
        project.progress_message = "Analysis complete"
        save_project(project)

        # Done
        project.status = ProjectStatus.COMPLETE
        _log(project, f"Analysis complete! {summary.total_metrics_extracted} metrics audited.", "🎉")
        save_project(project)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        project.status = ProjectStatus.ERROR
        project.error_message = str(e)
        project.progress_message = f"Error: {str(e)}"
        _log(project, f"Pipeline error: {str(e)}", "💥")
        save_project(project)
        raise


def _compute_summary(metrics: list[MetricRecord], source_docs: list[FileRef]) -> AuditSummary:
    """Compute aggregated audit statistics."""
    summary = AuditSummary(total_metrics_extracted=len(metrics))

    confidence_scores = []
    doc_coverage: dict[str, int] = {}
    reliability_dist: dict[str, int] = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0, "Tier 4": 0, "Unknown": 0}
    issue_slides = set()

    for m in metrics:
        v = m.verification
        if not v:
            summary.not_found += 1
            continue

        if v.status == VerificationStatus.VERIFIED:
            summary.verified += 1
        elif v.status == VerificationStatus.PARTIALLY_VERIFIED:
            summary.partially_verified += 1
            issue_slides.add(m.slide_number)
        elif v.status == VerificationStatus.UNVERIFIED:
            summary.unverified += 1
            issue_slides.add(m.slide_number)
        elif v.status == VerificationStatus.CONTRADICTED:
            summary.contradicted += 1
            issue_slides.add(m.slide_number)
        elif v.status == VerificationStatus.NOT_FOUND:
            summary.not_found += 1
            issue_slides.add(m.slide_number)

        confidence_scores.append(v.confidence_score)

        if v.matched_source_document_name:
            doc_coverage[v.matched_source_document_name] = doc_coverage.get(v.matched_source_document_name, 0) + 1

        if v.source_reliability:
            tier = v.source_reliability.tier.value
            reliability_dist[tier] = reliability_dist.get(tier, 0) + 1

    summary.avg_confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    summary.source_document_coverage = doc_coverage
    summary.reliability_distribution = reliability_dist
    summary.slides_with_issues = sorted(issue_slides)

    # Generate flags
    if summary.contradicted > 0:
        summary.flags.append(f"⚠️ {summary.contradicted} metric(s) CONTRADICTED by source documents — requires immediate review")
    if summary.unverified > 3:
        summary.flags.append(f"⚠️ {summary.unverified} metric(s) could not be verified — consider additional source documents")
    if summary.avg_confidence_score < 0.5:
        summary.flags.append("⚠️ Low average confidence — significant gaps in source coverage")

    return summary
