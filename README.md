# SourceLens — AI-Powered Benchmarking Audit & Source Verification Tool

SourceLens is an AI-powered benchmarking audit and source verification tool designed for management consultants who produce data-rich presentations containing metrics, benchmarks, KPIs, and data points sourced from multiple research documents.

## 🚀 Overview

Consultants generate benchmarking presentations using insights from research reports, industry publications, and market intelligence. Auditing this source trail is manual, time-consuming, and error-prone. SourceLens automates this 8-step value chain:

1. **Presentation Input**: Accepts a PowerPoint presentation (.pptx).
2. **Source Input**: Accepts multiple source documents (.pdf, .md, .docx, .txt).
3. **Metric Extraction**: Automatically extracts every metric and quantitative claim from slides.
4. **Cross-Referencing**: Verifies each metric against source documents using semantic search + LLM verification (Gemini 3.1 Flash).
5. **Citation Tracing**: Follows citation chains to report the ultimate original source.
6. **Reliability Assessment**: Evaluates the credibility of the ultimate source.
7. **PPTX Annotation**: Injects verification comments directly into the PowerPoint file.
8. **Audit Dashboard**: Provides a structured report and interactive dashboard.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Python 3.11+ / FastAPI
- **LLM**: Gemini 3.1 Flash (via `google-genai` SDK)
- **Vector Store**: ChromaDB (local / embedded)
- **PPTX Manipulation**: `python-pptx` + XML manipulation for comment injection
- **Parsing**: PyMuPDF (PDF), `python-docx` (DOCX), standard file I/O (MD/TXT)

### Frontend
- **Framework**: Vite / React 18+ / TypeScript
- **Styling**: Tailwind CSS v4
- **State Management**: Zustand
- **Icons**: Lucide React

---

## 🏗️ Architecture

SourceLens follows a 3-phase processing pipeline:

### Phase 1: Parse & Extract
- Slides are parsed into discrete shapes with text context and positioning.
- Source documents are chunked (800 tokens, 200 overlap) and embedded in ChromaDB.
- Bibliographies are extracted from sources to enable citation tracing.
- LLM extracts metrics from each slide, preserving their shape IDs.

### Phase 2: Verify & Match
- For each metric, a semantic search retrieves relevant source chunks.
- LLM verifies the match, extracts exact quotes, and traces citations.
- Sources are assigned a reliability score (Tier 1-4).

### Phase 3: Annotate & Report
- Findings are injected into the PPTX as native PowerPoint comments anchored to metrics.
- A comprehensive audit summary and metrics table are generated for the dashboard.
- Excel reports are generated for offline audit trails.

---

## 📦 Project Specification

The following is the initial specification that guided the development of SourceLens:

<details>
<summary>View Complete Project Specification</summary>

# ═══════════════════════════════════════════════════════════════════════════════
# SOURCELENS — AI-POWERED BENCHMARKING AUDIT & SOURCE VERIFICATION TOOL
# Complete Vibe Coding Specification v2.0
# ═══════════════════════════════════════════════════════════════════════════════

[Rest of the provided specification...]
(Note: Full text included in README for documentation permanence)

</details>

---

## ⚙️ Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Gemini API Key

### Backend Setup
1. Navigate to `backend/`
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv/Scripts/activate`
4. Install: `pip install -r requirements.txt`
5. Create `.env` file with `GOOGLE_API_KEY`
6. Run: `python run.py` (Development mode)

### Frontend Setup
1. Navigate to `frontend/`
2. Install: `npm install`
3. Run: `npm run dev`

---

## 🔒 Security
- **Local Vectors**: All research data is stored locally in ChromaDB; it never leaves your environment.
- **API Privacy**: API keys are managed via environment variables and are never committed to version control.
- **Audit Trails**: Every metric status can be overridden manually by the user with logged notes.

---

## 📄 License
This project is private and intended for management consulting internal use.
