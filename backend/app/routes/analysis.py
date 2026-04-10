"""
SourceLens — Analysis Routes
Pipeline execution, status polling, and metric retrieval endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.models import ProcessingStatusResponse, MetricOverride, VerificationStatus
from app.services.pipeline import get_project, save_project, run_analysis_pipeline

router = APIRouter(prefix="/api/projects", tags=["analysis"])


@router.post("/{project_id}/analyze")
async def start_analysis(project_id: str, background_tasks: BackgroundTasks):
    """Start the analysis pipeline as a background task."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.presentation_file:
        raise HTTPException(status_code=400, detail="No presentation uploaded")
    if not project.source_documents:
        raise HTTPException(status_code=400, detail="No source documents uploaded")

    # Start pipeline in background
    background_tasks.add_task(run_analysis_pipeline, project_id)

    project.status = "processing"
    project.progress_pct = 0
    project.progress_message = "Starting analysis..."
    save_project(project)

    return {"status": "started", "project_id": project_id}


@router.get("/{project_id}/status", response_model=ProcessingStatusResponse)
async def get_status(project_id: str):
    """Get current processing status and live log entries."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Return last 20 log entries
    recent_log = project.processing_log[-20:] if project.processing_log else []

    return ProcessingStatusResponse(
        status=project.status,
        progress_pct=project.progress_pct,
        progress_message=project.progress_message,
        current_phase=project.current_phase,
        log=recent_log,
        summary=project.summary_stats,
    )


@router.get("/{project_id}/metrics")
async def get_metrics(project_id: str):
    """Get all extracted metrics with their verification results."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return [m.model_dump() for m in project.metrics]


@router.get("/{project_id}/metrics/{metric_id}")
async def get_metric_detail(project_id: str, metric_id: str):
    """Get detailed information for a single metric."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for m in project.metrics:
        if m.metric_id == metric_id:
            return m.model_dump()

    raise HTTPException(status_code=404, detail="Metric not found")


@router.patch("/{project_id}/metrics/{metric_id}")
async def override_metric(project_id: str, metric_id: str, override: MetricOverride):
    """Allow user to manually override metric status/notes."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for m in project.metrics:
        if m.metric_id == metric_id:
            if m.verification:
                if override.status:
                    m.verification.status = override.status
                if override.notes:
                    m.verification.verification_notes = (
                        (m.verification.verification_notes or "") +
                        f"\n[Manual Override] {override.notes}"
                    )
            save_project(project)
            return m.model_dump()

    raise HTTPException(status_code=404, detail="Metric not found")


@router.get("/{project_id}/summary")
async def get_summary(project_id: str):
    """Get audit summary statistics."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.summary_stats:
        raise HTTPException(status_code=404, detail="Analysis not yet complete")
    return project.summary_stats.model_dump()


@router.get("/{project_id}/heatmap")
async def get_heatmap(project_id: str):
    """Get source coverage heatmap data."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build matrix: source docs × slides
    slide_numbers = sorted(set(m.slide_number for m in project.metrics))
    doc_names = [d.document_label or d.original_filename for d in project.source_documents]

    heatmap = {}
    for doc_name in doc_names:
        heatmap[doc_name] = {}
        for sn in slide_numbers:
            count = sum(
                1 for m in project.metrics
                if m.slide_number == sn
                and m.verification
                and m.verification.matched_source_document_name == doc_name
            )
            heatmap[doc_name][str(sn)] = count

    return {"slide_numbers": slide_numbers, "documents": doc_names, "matrix": heatmap}
