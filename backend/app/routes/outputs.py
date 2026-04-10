"""
SourceLens — Output/Download Routes
Endpoints for downloading annotated PPTX and Excel reports.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.services.pipeline import get_project

router = APIRouter(prefix="/api/projects", tags=["outputs"])


@router.get("/{project_id}/download/pptx")
async def download_pptx(project_id: str):
    """Download the annotated PPTX file with audit comments."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.annotated_pptx_path or not os.path.exists(project.annotated_pptx_path):
        raise HTTPException(status_code=404, detail="Annotated PPTX not yet generated")

    filename = os.path.basename(project.annotated_pptx_path)
    return FileResponse(
        project.annotated_pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@router.get("/{project_id}/download/excel")
async def download_excel(project_id: str):
    """Download the Excel audit report."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.excel_report_path or not os.path.exists(project.excel_report_path):
        raise HTTPException(status_code=404, detail="Excel report not yet generated")

    filename = os.path.basename(project.excel_report_path)
    return FileResponse(
        project.excel_report_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )
