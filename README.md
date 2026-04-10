# SourceLens
### AI-Powered Benchmarking Audit & Source Verification Tool

> Built for management consultants who need to verify every metric, benchmark, and data point in their presentations against original source documents — automatically.

---

## What Is SourceLens?

SourceLens is a full-stack web application that automates the source audit trail for data-rich consulting presentations. Upload a PowerPoint deck and one or more research documents, and SourceLens will:

- **Extract** every quantitative metric and claim from your slides
- **Verify** each metric against your source documents using semantic search + LLM reasoning
- **Trace** citation chains back to the ultimate original source
- **Score** each source for reliability (Tier 1–4)
- **Annotate** your PowerPoint with native review comments on each metric-containing shape
- **Export** a full audit report to Excel

The #1 output is the original PPTX returned with real PowerPoint comments (Review → Comments) injected directly onto the shapes — ready to share with your QA or client team.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS v4 |
| State | Zustand |
| Backend | Python 3.11 + FastAPI |
| LLM | **Gemini 3.1 Flash Lite** (`google-genai` SDK) |
| Embeddings | Google `text-embedding-004` (with OpenAI fallback) |
| Vector Store | ChromaDB (local, embedded — no external DB) |
| PPTX | `python-pptx` + `lxml` for comment injection |
| PDF Parsing | PyMuPDF (fitz) |

---

## Architecture

SourceLens follows a 3-phase processing pipeline:

```
Upload PPTX + Source Docs
        │
        ▼
┌──────────────────────────────────┐
│  Phase 1: Parse & Extract         │
│  ├─ Parse PPTX → shapes           │
│  ├─ Parse source docs → chunks    │
│  ├─ Embed chunks → ChromaDB       │
│  ├─ Extract bibliographies        │
│  └─ LLM: Extract metrics          │
└──────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────┐
│  Phase 2: Verify & Match          │
│  ├─ Semantic search per metric    │
│  ├─ LLM: Verify + exact quote     │
│  ├─ Trace citation chains         │
│  └─ Assess source reliability     │
└──────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────┐
│  Phase 3: Annotate & Report       │
│  ├─ Inject PPTX comments ⭐       │
│  ├─ Generate audit dashboard      │
│  └─ Export Excel report           │
└──────────────────────────────────┘
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Google AI Studio API key (free tier available at [aistudio.google.com](https://aistudio.google.com))

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Create .env file (never commit this!)
echo "GOOGLE_API_KEY=AIzaSy..." > .env

python run.py
# Server runs at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# UI runs at http://localhost:5173
```

---

## Configuration & API Keys

API keys are managed via:

1. **Local development**: Create `backend/.env` with `GOOGLE_API_KEY=your_key_here`. This file is listed in `.gitignore` and will **never** be committed to GitHub.

2. **Settings UI**: Open the ⚙️ Settings dialog in the app to enter API keys at runtime. You can also toggle **Demo Mode** to run without any key (uses regex-based heuristics).

3. **Deployment (Vercel/Railway)**: Add `GOOGLE_API_KEY` as an Environment Variable in your hosting provider's dashboard. It is injected securely at runtime — never stored in the repository.

> ⚠️ **Never hardcode API keys in source files.** The `.gitignore` is configured to block `.env` files from being tracked by Git.

---

## Demo Mode

No API key? No problem. Enable **Demo Mode** in Settings to run the full pipeline using:
- Regex-based metric extraction (finds real numbers/percentages from your slides)
- Text-matching heuristic verification against your source documents
- Mock citation chains and reliability scores

Demo Mode produces a realistic end-to-end audit without any LLM API calls.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/projects` | Create new project |
| `GET` | `/api/projects/{id}` | Get project + status |
| `POST` | `/api/projects/{id}/presentation` | Upload PPTX |
| `POST` | `/api/projects/{id}/sources` | Upload source documents |
| `POST` | `/api/projects/{id}/analyze` | Start analysis pipeline |
| `GET` | `/api/projects/{id}/status` | Poll processing status |
| `GET` | `/api/projects/{id}/metrics` | Get all verified metrics |
| `GET` | `/api/projects/{id}/download/pptx` | Download annotated PPTX |
| `GET` | `/api/projects/{id}/download/excel` | Download Excel audit report |
| `GET` | `/api/config` | Get current LLM config |
| `PUT` | `/api/config` | Update config / API keys |
| `POST` | `/api/config/test-api-key` | Validate an API key |

Full interactive docs available at `http://localhost:8000/docs` when the backend is running.

---

## Project Structure

```
SourceLens/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings & env var loading
│   │   ├── models.py            # Pydantic data models
│   │   ├── routes/
│   │   │   ├── projects.py      # Project CRUD
│   │   │   ├── files.py         # File upload handling
│   │   │   ├── analysis.py      # Analysis trigger & status
│   │   │   ├── outputs.py       # PPTX/Excel download
│   │   │   └── config_routes.py # API key management
│   │   ├── services/
│   │   │   ├── llm_client.py    # Unified Gemini/OpenAI client
│   │   │   ├── pipeline.py      # Main orchestration
│   │   │   ├── pptx_parser.py   # Slide parsing
│   │   │   ├── pptx_annotator.py# Comment injection
│   │   │   ├── document_parser.py
│   │   │   ├── chunker.py
│   │   │   ├── vector_store.py  # ChromaDB integration
│   │   │   ├── metric_extractor.py
│   │   │   ├── verifier.py
│   │   │   ├── bibliography.py
│   │   │   ├── citation_tracer.py
│   │   │   ├── reliability.py
│   │   │   └── excel_report.py
│   │   └── prompts/
│   │       └── templates.py     # All LLM prompt templates
│   ├── requirements.txt
│   ├── run.py
│   └── .gitignore               # Excludes .env and data/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/          # Header, nav
│   │   │   ├── upload/          # UploadPage
│   │   │   ├── processing/      # ProcessingView
│   │   │   ├── results/         # Dashboard, MetricTable
│   │   │   └── settings/        # SettingsDialog
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   └── types.ts         # TypeScript types
│   │   └── store/
│   │       └── useStore.ts      # Zustand global state
│   └── .gitignore               # Excludes node_modules, .env
└── README.md
```

---

## Security Notes

- All uploaded files and ChromaDB vectors are stored **locally** — nothing is sent to external services except LLM API calls (which contain only text excerpts, never full files).
- API keys are loaded from environment variables at server startup and are **never logged or returned by any API endpoint**.
- The `.gitignore` at the root and in both `backend/` and `frontend/` is configured to block all `.env*` files from Git tracking.

---

## Original Project Specification

The following is the complete original specification document that guided the development of SourceLens from scratch.

<details>
<summary>📋 Click to expand — SourceLens Complete Vibe Coding Specification v2.0</summary>

```
# ═══════════════════════════════════════════════════════════════════════════════
# SOURCELENS — AI-POWERED BENCHMARKING AUDIT & SOURCE VERIFICATION TOOL
# Complete Vibe Coding Specification v2.0
# ═══════════════════════════════════════════════════════════════════════════════
#
# This document is the single, self-contained specification for building
# SourceLens. It covers: project overview, architecture, data models, features,
# UI design, API endpoints, processing pipeline, LLM prompts, PowerPoint
# comment injection (with reference implementation), error handling, testing,
# file structure, and MVP scoping.
#
# Accompanying files provided alongside this spec:
#   1. Merck_KGaA_QMS_Benchmarking_PwC_April2026.pptx — test presentation
#      (contains 2 reference comments on Slide 2 — see Section 12)
#   2. Pharmaceutical_Quality_Deviation_CAPA_Benchmarking.pdf — example Deep
#      Research report (source document for testing)
#   3. (Optional) Manual audit table — expected output / ground truth
#


# SECTION 1: PROJECT OVERVIEW & OBJECTIVE

## 1.1 What Is SourceLens
SourceLens is a full-stack web application — an AI-powered benchmarking audit
and source verification tool designed for management consultants who produce
data-rich presentations (primarily PowerPoint decks) containing metrics,
benchmarks, KPIs, and data points sourced from multiple research documents.

## 1.2 The Core Problem
Consultants generate benchmarking presentations using insights from Deep
Research reports (AI-generated research documents from tools like Gemini,
ChatGPT, Claude, Copilot, Perplexity), industry publications, thought
leadership, market intelligence, and competitive analyses. These presentations
contain dozens or hundreds of individual metrics, each of which must be
traceable to a credible, verifiable source. Currently, auditing this source
trail is manual, time-consuming, and error-prone.

## 1.3 What This Tool Does — The 8-Step Value Chain
1. Accepts a PowerPoint presentation (.pptx) containing benchmarking data
2. Accepts one or more source/reference documents (.pdf, .md, .docx, .txt)
3. Automatically extracts every metric, data point, benchmark, and quantitative claim from each slide
4. Cross-references each extracted metric against all uploaded source documents using semantic search + LLM verification
5. Traces citation chains — if a source document itself cites an underlying source, the tool follows that chain
6. Assesses source reliability — evaluates whether each ultimate source is reputable, peer-reviewed, etc.
7. Generates an annotated PowerPoint with verification comments injected directly as real PowerPoint comments
8. Generates a structured audit report (HTML dashboard + downloadable Excel/CSV)

## 1.4 The #1 Output — PowerPoint Comments
The PRIMARY deliverable is the uploaded PowerPoint file returned with actual
PowerPoint review comments (Review → Comments) injected onto each shape
containing a benchmarking metric. Each comment contains the full source
audit trail. Everything else (dashboard, Excel report) is secondary.


# SECTION 2: TECHNOLOGY STACK

## 2.1 Frontend
- Framework: React 18+ with TypeScript
- UI Library: Tailwind CSS + shadcn/ui components
- State Management: Zustand
- File Upload: react-dropzone for drag-and-drop
- Data Display: Recharts for visualisations; TanStack Table for the audit table
- Export: Client-side Excel generation via SheetJS (xlsx)

## 2.2 Backend
- Runtime: Python 3.11+ with FastAPI
- PPTX Parsing & Writing: python-pptx for reading; lxml for comment injection
- PDF Parsing: PyMuPDF (fitz) as primary
- DOCX Parsing: python-docx
- Vector Store: ChromaDB (local, embedded) — no external database dependency
- Embeddings: Google text-embedding-004 (configurable)
- LLM Integration: Gemini 3.1 Flash Lite via google-genai SDK (configurable to OpenAI)
- Task Queue: FastAPI BackgroundTasks

## 2.3 Infrastructure
- Storage: Local filesystem; /data volume mount
- Configuration: Environment variables via .env file


# SECTION 3: DATA MODELS

## Project
{
  "project_id": "uuid",
  "project_name": "string",
  "created_at": "datetime",
  "status": "uploading | processing | phase1 | phase2 | phase3 | complete | error",
  "progress_pct": 0-100,
  "presentation_file": FileRef,
  "source_documents": [FileRef],
  "metrics": [MetricRecord],
  "summary_stats": AuditSummary
}

## FileRef
{
  "file_id": "uuid",
  "original_filename": "string",
  "file_type": "pptx | pdf | md | docx | txt",
  "document_type": "presentation | deep_research_report | article | whitepaper | market_research | regulatory_document | internal_analysis | other",
  "document_label": "string — user-provided short name",
  "page_count": int,
  "chunk_count": int,
  "has_bibliography": boolean,
  "bibliography_entries": [BibEntry]
}

## BibEntry
{
  "ref_id": "string — e.g. '[1]', '[28]'",
  "ref_text": "string — full citation text",
  "authors": "string",
  "title": "string",
  "publication": "string",
  "year": "string",
  "url": "string",
  "source_type": "peer_reviewed | industry_report | consultancy_publication | regulatory_document | news_article | conference_paper | company_publication | unknown",
  "reliability_tier": "Tier 1 | Tier 2 | Tier 3 | Tier 4 | Unknown"
}

## MetricRecord
{
  "metric_id": "uuid",
  "slide_number": int,
  "slide_title": "string",
  "shape_id": "string — python-pptx shape identifier for comment injection",
  "shape_text_context": "string",
  "extracted_metric": {
    "value": "string — e.g. '90–131 days', '30–40%', '$8M–$12M'",
    "metric_type": "percentage | currency | duration | ratio | count | range | qualitative_benchmark",
    "description": "string",
    "context_sentence": "string"
  },
  "slide_source_tag": "string | null",
  "verification": {
    "status": "verified | partially_verified | unverified | contradicted | not_found",
    "confidence_score": 0.0–1.0,
    "matched_source_document": "file_id | null",
    "matched_location": {
      "page_number": "int | null",
      "section_heading": "string | null",
      "chunk_text": "string",
      "exact_quote": "string"
    },
    "citation_chain": {
      "intermediate_source": "string",
      "intermediate_ref_id": "string",
      "ultimate_source": "string",
      "ultimate_source_type": "string",
      "ultimate_source_url": "string | null"
    },
    "source_reliability": {
      "tier": "Tier 1 | Tier 2 | Tier 3 | Tier 4 | Unknown",
      "tier_label": "Gold Standard | Established & Reputable | Acceptable / Niche | Caution / Unverifiable | Unknown",
      "stars": 1–5,
      "reasoning": "string",
      "recommendation": "string"
    },
    "verification_notes": "string",
    "llm_reasoning": "string"
  }
}


# SECTION 4: FILE UPLOAD INTERFACE

## 4.1 Presentation Upload (Left Panel)
- Accept exactly ONE .pptx file
- Display: filename, file size, slide count
- Show thumbnail previews of each slide
- Allow user to EXCLUDE specific slides from analysis via checkbox toggles

## 4.2 Source Document Upload (Right Panel)
- Accept MULTIPLE files: .pdf, .md, .docx, .txt
- For each file, user provides: Document Label + Document Type (dropdown)
- Show a "Ready to Analyse" button when at least 1 PPTX + 1 source are uploaded


# SECTION 5: PHASE 1 — PARSE & EXTRACT

## 5.1 PPTX Parsing
Use python-pptx to iterate every slide and shape. CRITICAL: preserve shape_id
AND position (left, top, width, height) — needed for comment injection.

## 5.2 Source Document Chunking
- Chunk size: 800 tokens with 200-token overlap
- Prefer splitting on headings/paragraph boundaries; never mid-sentence
- Embed all chunks using configured model → store in ChromaDB with metadata

## 5.3 Bibliography Extraction
Detect reference section headers ("References", "Bibliography", "Sources", etc.)
Parse each reference entry. Use LLM when regex fails.

LLM Prompt — Bibliography Extraction:
  "You are a citation parser. Extract each reference into structured JSON with:
   ref_id, full_text, authors, title, publication, year, url, source_type.
   BIBLIOGRAPHY TEXT: {bibliography_text}"

## 5.4 Metric Extraction from Slides
Send all shapes on each slide to LLM for metric extraction.

LLM Prompt — Metric Extraction:
  "You are a precision data extraction system for consulting presentations.
   Extract EVERY quantitative metric, benchmark, and data point.
   SLIDE {slide_number}: "{slide_title}"
   SLIDE CONTENT: {all_shape_texts}
   
   For each metric: shape_id, value, metric_type, description,
   context_sentence, slide_source_tag.
   
   DO NOT extract: page numbers, timestamps, generic labels, branding text.
   Return as JSON array. Be exhaustive."

### Edge Cases Handled:
- Simple %: "30–40% fewer deviations" → value: "30–40%"
- Currency range: "$8M–$12M" → type: currency
- Duration range: "90–131 days" → type: duration
- Fractions: "1/6th of median" → type: ratio
- Combined stats: "208 sites, 52 countries" → TWO metrics
- Before/After: "5–10 days → 1–3 days" → TWO metrics


# SECTION 6: PHASE 2 — VERIFY & MATCH

## 6.1 Semantic Search
Query ChromaDB with metric context_sentence + description. Retrieve top 8 chunks.

## 6.2 LLM Verification
Send metric + retrieved chunks to LLM.

LLM Prompt — Metric Verification:
  "You are a meticulous fact-checking auditor for a management consulting firm.
   
   METRIC TO VERIFY:
   - Value: {metric.value}
   - Description: {metric.description}
   - Context: {metric.context_sentence}
   - Slide source tag: {metric.slide_source_tag}
   
   SOURCE EXCERPTS: {chunks}
   
   Tasks:
   1. MATCH ASSESSMENT: exact match, equivalent expression, rounded version?
   2. EXACT QUOTE: verbatim passage supporting/contradicting the metric
   3. CITATION CHAIN: if source cites an underlying source, identify it
   4. DISCREPANCY CHECK: is the slide an accurate representation?
   5. SOURCE ATTRIBUTION CHECK: is the slide's source tag correct?
   6. VERIFICATION STATUS: verified | partially_verified | unverified | contradicted | not_found
   7. CONFIDENCE SCORE: 0.0–1.0
   
   Return as JSON."

## 6.3 Source Reliability Assessment

LLM Prompt — Reliability:
  "Assess the reliability of this source for pharma/life-sciences benchmarking.
   
   RELIABILITY TIERS:
   Tier 1 — Gold Standard (5★): Peer-reviewed journals, FDA/EMA/ICH guidelines,
     large validated benchmarking programmes (McKinsey POBOS, St. Gallen OPEX)
   Tier 2 — Established & Reputable (4★): Major consulting firm reports (McKinsey,
     BCG, PwC), established industry bodies (ISPE, PDA, MDIC), government data
   Tier 3 — Acceptable / Niche (3★): Niche trade journals, smaller consultancy
     whitepapers, company case studies, conference presentations
   Tier 4 — Caution / Unverifiable (2★): Blog posts, undisclosed methodology,
     self-reported data, AI-generated content without underlying citations
   Unknown (1★): Cannot determine provenance
   
   Return: tier, tier_label, stars, reasoning, recommendation."

## 6.4 Citation Chain Resolution
Check matched text for reference markers ([1], (ref [9]), (McKinsey, 2024)).
Look up in document bibliography. Use LLM for Deep Research reports.


# SECTION 7: PHASE 3 — ANNOTATE & REPORT

## 7.1 PowerPoint Comment Injection — PRIMARY OUTPUT

Comment format:
  [SourceLens Audit]
  
  METRIC: {value} — {description}
  STATUS: {emoji} {STATUS} (confidence: {score}%)
  
  SOURCE TRAIL:
  ├─ Found in: {matched_source_document_name}
  │  Page: {page_number}
  │  Quote: "{exact_quote}"
  │
  ├─ Reference: {intermediate_ref_id} in {intermediate_source}
  │
  └─ Original Source: {ultimate_source}
     Reliability: {stars} {tier} — {tier_label}
  
  ⚠️ NOTE: {discrepancies}
  💡 RECOMMENDATION: {recommendation}

Status emojis: ✅ verified | ⚠️ partially_verified | ❌ unverified | 🚫 contradicted | ❓ not_found

Comment positioning:
  x = shape.left + (shape.width / 2)
  y = shape.top

ALWAYS preserve existing comments. New SourceLens comments are ADDED alongside.

## 7.2 Interactive Dashboard
- Summary stats bar (verified/partial/unverified/contradicted counts)
- Slide navigator with colour-coded badges
- Metric audit table (sortable, filterable)
- Detail slide-out panel per metric
- Source coverage heatmap

## 7.3 Downloadable Reports
- Annotated PPTX (PRIMARY)
- Excel report (Summary, Metric Detail, Source Index, Bibliography Chain, Issues)


# SECTION 8: USER INTERFACE DESIGN

## 8.1 Layout
- Top nav: Logo, project name, settings ⚙️, dark mode toggle
- Three-step wizard: Upload → Processing → Results

## 8.2 Processing View
Real-time progress tracker with live feed of verification results.


# SECTION 9: API ENDPOINTS

POST   /api/projects                           — Create project
GET    /api/projects/{id}                      — Get project + status
POST   /api/projects/{id}/presentation         — Upload PPTX
POST   /api/projects/{id}/sources              — Upload source docs
POST   /api/projects/{id}/analyze              — Start pipeline
GET    /api/projects/{id}/status               — Poll progress
GET    /api/projects/{id}/metrics              — Get all results
PATCH  /api/projects/{id}/metrics/{mid}        — User override
GET    /api/projects/{id}/download/pptx        — Annotated PPTX
GET    /api/projects/{id}/download/excel       — Excel report
GET    /api/config                             — Get config
PUT    /api/config                             — Update config / API keys
POST   /api/config/test-api-key               — Validate API key


# SECTION 10: ERROR HANDLING

## File Handling
- Corrupted PPTX: Catch exceptions, user-friendly error
- Scanned PDFs (no text): Warn user OCR is needed
- Large files: Upload limits (PPTX: 100MB; source docs: 50MB each)

## LLM Handling
- Rate limits: Exponential backoff with jitter
- Token limits: Truncate intelligently using embedding similarity scores
- Hallucination guard: After LLM claims "verified" with exact quote,
  programmatically check that the quoted text actually exists in the source chunk.
  If not → downgrade to "partially_verified" and flag it.

## Comment Injection Edge Cases
- Multiple metrics in same shape → ONE comment with all audit trails concatenated
- Existing comments → ALWAYS preserve, NEVER delete


# SECTION 11: POWERPOINT COMMENT INJECTION — TECHNICAL

## Comment System
A .pptx is a ZIP archive. Comments require 3 XML components:

1. ppt/commentAuthors.xml — defines comment authors
   <p:cmAuthorLst>
     <p:cmAuthor id="1" name="SourceLens Audit" initials="SL" lastIdx="0" clrIdx="0"/>
   </p:cmAuthorLst>

2. ppt/comments/comment{N}.xml — one per slide with comments
   <p:cmLst>
     <p:cm authorId="1" dt="2026-04-03T12:00:00.000" idx="1">
       <p:pos x="2400" y="1200"/>
       <p:text>[SourceLens Audit] ...</p:text>
     </p:cm>
   </p:cmLst>

3. ppt/slides/_rels/slide{N}.xml.rels — relationship linking slide to comments
   <Relationship Type=".../relationships/comments" Target="../comments/comment{N}.xml"/>

## Legacy vs Modern Comments
- Legacy (Office 2007-2019): ppt/comments/ — simple text, maximum compatibility
- Modern (Office 365+): ppt/comments/modernComment{N}.xml — threaded, @mentions
- CHECK the existing PPTX format first and replicate it exactly.

## Python Implementation
Use python-pptx's underlying OPC layer + lxml to manipulate XML parts directly.
Do NOT use python-pptx's comment API (incomplete). Manipulate the ZIP XML directly.

RT_COMMENT_AUTHORS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/commentAuthors'
RT_COMMENTS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments'
CONTENT_TYPE_AUTHORS = 'application/vnd.openxmlformats-officedocument.presentationml.commentAuthors+xml'
CONTENT_TYPE_COMMENTS = 'application/vnd.openxmlformats-officedocument.presentationml.comments+xml'

## Verification Test
After injection, open in PowerPoint and confirm:
- Original comments on Slide 2 are STILL present and unchanged
- SourceLens audit comments appear on all content slides
- ALL comments visible in Review → Comments panel
- Clicking navigates to correct shape
- Text is fully readable (no encoding issues)
```

</details>

---

## License

This project is private and intended for management consulting internal use.
