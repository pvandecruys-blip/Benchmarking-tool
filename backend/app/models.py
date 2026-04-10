"""
SourceLens Data Models
Complete Pydantic models for the entire application data layer.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import uuid


# ─── Enums ────────────────────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PHASE1 = "phase1"
    PHASE2 = "phase2"
    PHASE3 = "phase3"
    COMPLETE = "complete"
    ERROR = "error"


class FileType(str, Enum):
    PPTX = "pptx"
    PDF = "pdf"
    MD = "md"
    DOCX = "docx"
    TXT = "txt"


class DocumentType(str, Enum):
    PRESENTATION = "presentation"
    DEEP_RESEARCH_REPORT = "deep_research_report"
    ARTICLE = "article"
    WHITEPAPER = "whitepaper"
    MARKET_RESEARCH = "market_research"
    REGULATORY_DOCUMENT = "regulatory_document"
    INTERNAL_ANALYSIS = "internal_analysis"
    OTHER = "other"


class MetricType(str, Enum):
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    DURATION = "duration"
    RATIO = "ratio"
    COUNT = "count"
    RANGE = "range"
    QUALITATIVE_BENCHMARK = "qualitative_benchmark"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    NOT_FOUND = "not_found"


class ReliabilityTier(str, Enum):
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"
    TIER_4 = "Tier 4"
    UNKNOWN = "Unknown"


class SourceType(str, Enum):
    PEER_REVIEWED = "peer_reviewed"
    INDUSTRY_REPORT = "industry_report"
    CONSULTANCY_PUBLICATION = "consultancy_publication"
    REGULATORY_DOCUMENT = "regulatory_document"
    NEWS_ARTICLE = "news_article"
    CONFERENCE_PAPER = "conference_paper"
    COMPANY_PUBLICATION = "company_publication"
    UNKNOWN = "unknown"


# ─── Core Models ──────────────────────────────────────────────────────────────

class BibEntry(BaseModel):
    """Extracted bibliography/reference entry from a source document."""
    ref_id: str = ""
    ref_text: str = ""
    authors: str = ""
    title: str = ""
    publication: str = ""
    year: str = ""
    url: str = ""
    source_type: SourceType = SourceType.UNKNOWN
    reliability_tier: ReliabilityTier = ReliabilityTier.UNKNOWN


class FileRef(BaseModel):
    """Reference to an uploaded file."""
    file_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str = ""
    file_type: FileType = FileType.PDF
    file_path: str = ""
    file_size_bytes: int = 0
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    document_type: DocumentType = DocumentType.OTHER
    document_label: str = ""
    page_count: int = 0
    chunk_count: int = 0
    has_bibliography: bool = False
    bibliography_entries: list[BibEntry] = Field(default_factory=list)


class ShapePosition(BaseModel):
    """Position and dimensions of a shape on a slide (in EMUs)."""
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0


class SlideShape(BaseModel):
    """A shape extracted from a PPTX slide."""
    shape_id: int = 0
    shape_name: str = ""
    text: str = ""
    table: Optional[list[list[str]]] = None
    position: ShapePosition = Field(default_factory=ShapePosition)


class SlideRecord(BaseModel):
    """A parsed slide from the presentation."""
    slide_number: int = 0
    slide_title: str = ""
    slide_id: int = 0  # Internal PPTX slide ID for comment anchoring
    shapes: list[SlideShape] = Field(default_factory=list)
    excluded: bool = False
    all_text: str = ""  # Concatenated text from all shapes


class ExtractedMetric(BaseModel):
    """A single extracted metric/data point."""
    value: str = ""
    metric_type: MetricType = MetricType.PERCENTAGE
    description: str = ""
    context_sentence: str = ""


class MatchedLocation(BaseModel):
    """Location within a source document where a metric was found."""
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    chunk_text: str = ""
    exact_quote: str = ""


class CitationChain(BaseModel):
    """The citation trail from slide → source doc → ultimate source."""
    intermediate_source: Optional[str] = None
    intermediate_ref_id: Optional[str] = None
    ultimate_source: Optional[str] = None
    ultimate_source_type: Optional[str] = None
    ultimate_source_url: Optional[str] = None


class SourceReliability(BaseModel):
    """Reliability assessment of the ultimate source."""
    tier: ReliabilityTier = ReliabilityTier.UNKNOWN
    tier_label: str = "Unknown"
    stars: int = 1
    reasoning: str = ""
    recommendation: str = ""


class Verification(BaseModel):
    """Complete verification result for a single metric."""
    status: VerificationStatus = VerificationStatus.NOT_FOUND
    confidence_score: float = 0.0
    matched_source_document: Optional[str] = None
    matched_source_document_name: Optional[str] = None
    matched_location: Optional[MatchedLocation] = None
    citation_chain: Optional[CitationChain] = None
    source_reliability: Optional[SourceReliability] = None
    verification_notes: str = ""
    llm_reasoning: str = ""


class MetricRecord(BaseModel):
    """Complete record for a single extracted and verified metric."""
    metric_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    slide_number: int = 0
    slide_title: str = ""
    shape_id: int = 0
    shape_text_context: str = ""
    extracted_metric: ExtractedMetric = Field(default_factory=ExtractedMetric)
    slide_source_tag: Optional[str] = None
    verification: Optional[Verification] = None


class AuditSummary(BaseModel):
    """Aggregated audit statistics."""
    total_metrics_extracted: int = 0
    verified: int = 0
    partially_verified: int = 0
    unverified: int = 0
    contradicted: int = 0
    not_found: int = 0
    avg_confidence_score: float = 0.0
    source_document_coverage: dict[str, int] = Field(default_factory=dict)
    reliability_distribution: dict[str, int] = Field(default_factory=dict)
    slides_with_issues: list[int] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class Project(BaseModel):
    """Top-level project containing everything."""
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = "Untitled Project"
    created_at: datetime = Field(default_factory=datetime.now)
    status: ProjectStatus = ProjectStatus.UPLOADING
    progress_pct: int = 0
    progress_message: str = ""
    current_phase: str = ""
    presentation_file: Optional[FileRef] = None
    source_documents: list[FileRef] = Field(default_factory=list)
    slides: list[SlideRecord] = Field(default_factory=list)
    metrics: list[MetricRecord] = Field(default_factory=list)
    summary_stats: Optional[AuditSummary] = None
    error_message: Optional[str] = None
    annotated_pptx_path: Optional[str] = None
    excel_report_path: Optional[str] = None

    # Processing log entries for live feed
    processing_log: list[dict[str, Any]] = Field(default_factory=list)


# ─── API Request/Response Models ─────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    project_name: str = "Untitled Project"


class UpdateConfigRequest(BaseModel):
    openai_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    verification_strictness: Optional[str] = None
    chunk_size: Optional[int] = None
    max_chunks_per_query: Optional[int] = None


class SourceDocumentUploadMeta(BaseModel):
    document_label: str = ""
    document_type: DocumentType = DocumentType.OTHER


class MetricOverride(BaseModel):
    status: Optional[VerificationStatus] = None
    notes: Optional[str] = None


class ProjectSummaryResponse(BaseModel):
    project_id: str
    project_name: str
    created_at: datetime
    status: ProjectStatus
    progress_pct: int
    progress_message: str = ""
    total_metrics: int = 0
    presentation_filename: Optional[str] = None
    source_doc_count: int = 0


class ProcessingStatusResponse(BaseModel):
    status: ProjectStatus
    progress_pct: int
    progress_message: str = ""
    current_phase: str = ""
    log: list[dict[str, Any]] = Field(default_factory=list)
    summary: Optional[AuditSummary] = None
