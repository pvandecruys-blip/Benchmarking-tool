"""
SourceLens — Project Routes
CRUD endpoints for project management.
"""

from fastapi import APIRouter, HTTPException
from app.models import (
    Project, CreateProjectRequest, ProjectSummaryResponse, ProjectStatus
)
from app.services.pipeline import get_project, get_all_projects, save_project, delete_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectSummaryResponse)
async def create_project(req: CreateProjectRequest):
    """Create a new analysis project."""
    project = Project(project_name=req.project_name)
    save_project(project)
    return _to_summary(project)


@router.get("", response_model=list[ProjectSummaryResponse])
async def list_projects():
    """List all projects."""
    return [_to_summary(p) for p in get_all_projects()]


@router.get("/{project_id}")
async def get_project_detail(project_id: str):
    """Get full project details including metrics."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump()


@router.delete("/{project_id}")
async def remove_project(project_id: str):
    """Delete a project and all its data."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    delete_project(project_id)
    return {"status": "deleted"}


def _to_summary(p: Project) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        project_id=p.project_id,
        project_name=p.project_name,
        created_at=p.created_at,
        status=p.status,
        progress_pct=p.progress_pct,
        progress_message=p.progress_message,
        total_metrics=len(p.metrics),
        presentation_filename=p.presentation_file.original_filename if p.presentation_file else None,
        source_doc_count=len(p.source_documents),
    )
