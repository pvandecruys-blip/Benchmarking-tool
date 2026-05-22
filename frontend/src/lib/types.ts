// SourceLens TypeScript Type Definitions

export type ProjectStatus = 'uploading' | 'processing' | 'phase1' | 'phase2' | 'phase3' | 'complete' | 'error';
export type VerificationStatus = 'verified' | 'partially_verified' | 'unverified' | 'contradicted' | 'not_found';
export type DocumentType = 'presentation' | 'deep_research_report' | 'article' | 'whitepaper' | 'market_research' | 'regulatory_document' | 'internal_analysis' | 'other';
export type MetricType = 'percentage' | 'currency' | 'duration' | 'ratio' | 'count' | 'range' | 'qualitative_benchmark';

export interface ProjectSummary {
  project_id: string;
  project_name: string;
  created_at: string;
  status: ProjectStatus;
  progress_pct: number;
  progress_message: string;
  total_metrics: number;
  presentation_filename: string | null;
  source_doc_count: number;
}

export interface FileUploadResult {
  file_id: string;
  filename: string;
  size_bytes: number;
  slide_count?: number;
  document_label?: string;
  document_type?: string;
}

export interface SlidePreview {
  slide_number: number;
  slide_title: string;
  excluded: boolean;
  text_preview: string;
  shape_count: number;
}

export interface MatchedLocation {
  page_number: number | null;
  section_heading: string | null;
  chunk_text: string;
  exact_quote: string;
}

export interface CitationChain {
  intermediate_source: string | null;
  intermediate_ref_id: string | null;
  ultimate_source: string | null;
  ultimate_source_type: string | null;
  ultimate_source_url: string | null;
}

export interface SourceReliability {
  tier: string;
  tier_label: string;
  stars: number;
  reasoning: string;
  recommendation: string;
}

export interface Verification {
  status: VerificationStatus;
  confidence_score: number;
  matched_source_document: string | null;
  matched_source_document_name: string | null;
  matched_location: MatchedLocation | null;
  citation_chain: CitationChain | null;
  source_reliability: SourceReliability | null;
  verification_notes: string;
  llm_reasoning: string;
}

export interface ExtractedMetric {
  value: string;
  metric_type: MetricType;
  description: string;
  context_sentence: string;
}

export interface MetricRecord {
  metric_id: string;
  slide_number: number;
  slide_title: string;
  shape_id: number;
  shape_text_context: string;
  extracted_metric: ExtractedMetric;
  slide_source_tag: string | null;
  verification: Verification | null;
}

export interface AuditSummary {
  total_metrics_extracted: number;
  verified: number;
  partially_verified: number;
  unverified: number;
  contradicted: number;
  not_found: number;
  avg_confidence_score: number;
  source_document_coverage: Record<string, number>;
  reliability_distribution: Record<string, number>;
  slides_with_issues: number[];
  flags: string[];
}

export interface ProcessingStatus {
  status: ProjectStatus;
  progress_pct: number;
  progress_message: string;
  current_phase: string;
  log: LogEntry[];
  summary: AuditSummary | null;
}

export interface LogEntry {
  timestamp: string;
  message: string;
  emoji: string;
}

export interface SourceDoc {
  file_id: string;
  original_filename: string;
  document_label: string;
  document_type: DocumentType;
  file_size_bytes: number;
}

export interface AppConfig {
  llm_provider: string;
  llm_model: string;
  embedding_model: string;
  verification_strictness: string;
  chunk_size: number;
  max_chunks_per_query: number;
  has_api_key: boolean;
  has_google_key: boolean;
  has_openai_key: boolean;
  demo_mode: boolean;
  available_models: Record<string, { label: string; provider: string; cost_tier: string }>;
}

// ──────────────────────────────────────────────────────────────────
// Parser output types (Phase 2: in-browser document parsing)
// Mirrors backend/app/models.py SlideRecord/SlideShape and the dict
// shape returned by document_parser.py.
// ──────────────────────────────────────────────────────────────────

export interface SlideShape {
  shape_id: number;
  shape_name: string;
  text: string;
  table: string[][] | null;
}

export interface SlideRecord {
  slide_number: number;
  slide_title: string;
  slide_id: string;
  shapes: SlideShape[];
  all_text: string;
  excluded: boolean;
}

export interface ParsedPresentation {
  filename: string;
  size_bytes: number;
  slides: SlideRecord[];
}

export interface ParsedDocument {
  filename: string;
  size_bytes: number;
  text: string;
  pages: string[];
  page_count: number;
}
