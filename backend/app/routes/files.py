"""
SourceLens — File Upload Routes
Handles PPTX presentation and source document uploads.
"""

import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models import FileRef, FileType, DocumentType
from app.services.pipeline import get_project, save_project
from app.services.pptx_parser import get_slide_count
from app.config import get_settings

router = APIRouter(prefix="/api/projects", tags=["files"])


@router.post("/{project_id}/presentation")
async def upload_presentation(project_id: str, file: UploadFile = File(...)):
    """Upload a PPTX presentation file."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename or not file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files are accepted")

    settings = get_settings()

    # Save file
    project_dir = os.path.join(settings.upload_dir, project_id)
    os.makedirs(project_dir, exist_ok=True)
    file_path = os.path.join(project_dir, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Validate file was actually written properly
    if len(content) < 1024:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"File too small ({len(content)} bytes) — appears corrupted")

    # Get slide count
    try:
        slide_count = get_slide_count(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid PPTX file: {str(e)}")

    file_ref = FileRef(
        original_filename=file.filename,
        file_type=FileType.PPTX,
        file_path=file_path,
        file_size_bytes=len(content),
        document_type=DocumentType.PRESENTATION,
        document_label=file.filename,
        page_count=slide_count,
    )
    project.presentation_file = file_ref
    save_project(project)

    return {
        "file_id": file_ref.file_id,
        "filename": file.filename,
        "size_bytes": len(content),
        "slide_count": slide_count,
    }


@router.post("/{project_id}/sources")
async def upload_source_document(
    project_id: str,
    file: UploadFile = File(...),
    document_label: str = Form(""),
    document_type: str = Form("other"),
):
    """Upload a source document (PDF, DOCX, MD, TXT)."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Determine file type
    ext = os.path.splitext(file.filename)[1].lower()
    file_type_map = {".pdf": FileType.PDF, ".docx": FileType.DOCX, ".md": FileType.MD, ".txt": FileType.TXT}
    file_type = file_type_map.get(ext)
    if not file_type:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Accepted: .pdf, .docx, .md, .txt")

    # Parse document type
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.OTHER

    settings = get_settings()
    project_dir = os.path.join(settings.upload_dir, project_id)
    os.makedirs(project_dir, exist_ok=True)
    file_path = os.path.join(project_dir, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    file_ref = FileRef(
        original_filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        file_size_bytes=len(content),
        document_type=doc_type,
        document_label=document_label or file.filename,
    )
    project.source_documents.append(file_ref)
    save_project(project)

    return {
        "file_id": file_ref.file_id,
        "filename": file.filename,
        "size_bytes": len(content),
        "document_label": file_ref.document_label,
        "document_type": doc_type.value,
    }


@router.delete("/{project_id}/sources/{file_id}")
async def remove_source_document(project_id: str, file_id: str):
    """Remove a source document from the project."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.source_documents = [d for d in project.source_documents if d.file_id != file_id]
    save_project(project)
    return {"status": "removed"}


@router.get("/{project_id}/slides")
async def get_slides(project_id: str):
    """Get parsed slide previews."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.slides:
        return [
            {
                "slide_number": s.slide_number,
                "slide_title": s.slide_title,
                "excluded": s.excluded,
                "text_preview": s.all_text[:300],
                "shape_count": len(s.shapes),
            }
            for s in project.slides
        ]

    # Parse if not yet done
    if project.presentation_file:
        from app.services.pptx_parser import parse_pptx
        slides = parse_pptx(project.presentation_file.file_path)
        project.slides = slides
        save_project(project)
        return [
            {
                "slide_number": s.slide_number,
                "slide_title": s.slide_title,
                "excluded": s.excluded,
                "text_preview": s.all_text[:300],
                "shape_count": len(s.shapes),
            }
            for s in slides
        ]

    return []
