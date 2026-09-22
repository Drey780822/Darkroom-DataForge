# DARKROOM DATAFORGE
### Wits–merSETA Darkroom • Intelligent Document → Structured Data Platform

![Architecture](https://img.shields.io/badge/Architecture-FastAPI%20%2B%20React%2018%20%2B%20TypeScript-1D3557?style=flat-square)
![LLM Providers](https://img.shields.io/badge/AI%20Providers-DeepSeek%20%7C%20Claude%20%7C%20Gemini%20%7C%20Groq%20%7C%20Ollama-D4AF37?style=flat-square)
![Provenance](https://img.shields.io/badge/Provenance-Page--level%20Sync%20(%23page%3DN)-22C55E?style=flat-square)
![Validation](https://img.shields.io/badge/Validation-Deterministic%20%2B%20Multi--Model%20Reconciliation-0ea5e9?style=flat-square)
![Testing](https://img.shields.io/badge/Tests-46%20Passed%20(100%25)-green?style=flat-square)

---

## 1. Overview & Purpose

**Darkroom DataForge** is a centralized document-intelligence and structured dataset workstation built specifically for the **Wits–merSETA Darkroom** research team.

The platform transforms complex, semi-structured documents—such as **Public TVET College Occupational Qualifications lists**, **Organising Framework for Occupations (OFO) gazettes**, **Occupations in High Demand (OIHD) reports**, and **survey codebooks**—into clean, validated, machine-readable datasets (CSV, Excel, JSON, and SQL databases).

Unlike simplistic "PDF to Excel" converters or naive consumer chatbots that hallucinate or drop rows, Darkroom DataForge functions as a scientific data-engineering workstation:
- **PDF as the Single Source of Truth**: The AI is strictly constrained to extract verbatim values and is forbidden from guessing or inventing data.
- **Code & Format Integrity**: Critical South African identifiers (6-digit OFO codes like `021301`, SAQA IDs like `0042`, NQF levels 1–10) have their **leading zeroes and formatting preserved**.
- **Table-Aware Chunking**: Slices long tables across pages with contextual overlap so wrapped rows, split cells, and carried-over sub-headers are reconstructed accurately.
- **Multi-Model Check & Reconciliation**: In High-Accuracy mode, two independent models (e.g. Claude 3.7 Sonnet and Gemini 2.5 Flash) extract the same pages. Agreement rates are calculated and discrepancies flagged for human resolution.
- **Human-in-the-Loop Review**: Discrepancies and validation warnings link directly to the source PDF page (`#page=N`) for one-click verification and formal researcher sign-off.
- **Full Research Export Bundle**: Outputs not just a spreadsheet, but a complete research package including `data_dictionary.csv`, `provenance.csv`, and `extraction_manifest.json`.

---

## 2. The 8-Stage Extraction Pipeline

```
[ Source PDF Document(s) ]
           ↓
Stage 1: Document Inspection & Layout Analysis (Text density, OCR check, continuation tables)
           ↓
Stage 2: Document Understanding (Pass 1 - Purpose, sections, candidate datasets, annexures)
           ↓
Stage 3: Interactive Schema Inference (Pass 2 - Field names, types, primary keys, leading zeroes)
           ↓
Stage 4: Table-Aware Chunking (Continuation overlap & SHA-256 chunk caching)
           ↓
Stage 5: LLM Structured Extraction (Strict Pydantic JSON contract, verbatim source values)
           ↓
Stage 6: Dual Validation (Deterministic SAQA/OFO/NQF rules + LLM consistency self-check)
           ↓
Stage 7: Multi-Model Reconciliation (Cross-model comparison & agreement scoring)
           ↓
Stage 8: Human-in-the-Loop Review Queue (1-Click #page=N verification & sign-off)
           ↓
[ Verified Research Dataset + Provenance Bundle ]
```

---

## 3. Supported AI Providers & Privacy Modes

Configure any of the following providers in the web interface under **AI Models & LLMs** (`/ai-models`) or via `.env`:

| Provider | Supported Models | Primary Use Case |
| :--- | :--- | :--- |
| **Local Ollama** | `llama3.1`, `qwen2.5`, `mistral`, `deepseek-r1` | **100% Local & Air-Gapped**: Zero data leaves your machine. Essential for sensitive, unpublished research data. |
| **DeepSeek** | `deepseek-chat` (V3), `deepseek-reasoner` (R1) | Complex mathematical, codebook, and structural extraction at very low cost. |
| **Google Gemini** | `gemini-2.5-flash`, `gemini-2.5-pro` | Multimodal OCR, 1M+ context window, ultra-fast table parsing. |
| **Anthropic Claude**| `claude-3-7-sonnet-20250219`, `claude-3-5-haiku` | Highest precision, extended reasoning, difficult table layouts. |
| **Groq Cloud** | `llama-3.3-70b-versatile`, `deepseek-r1-distill-70b` | Ultra-high-speed LPU inference for high-throughput batch extraction. |
| **OpenAI / Router** | `gpt-4o`, `gpt-4o-mini`, OpenRouter gateway | General-purpose commercial model access. |

> **Security Note:** All API keys are saved on the server in `storage/ai_credentials.json` (which is gitignored). Keys are masked on read and never exposed to the frontend browser.

---

## 4. Workstation Architecture & Monorepo Structure

```
Darkroom DataForge/
├── backend/
│   ├── app/
│   │   ├── api/v1/                     # REST API endpoints
│   │   │   ├── ai_models.py            # Provider credentials, available models, connection testing
│   │   │   ├── datasets.py             # Datasets CRUD & verification sign-off
│   │   │   ├── documents.py            # PDF upload, streaming, inspection
│   │   │   ├── evaluation.py           # Golden dataset benchmarking runner
│   │   │   ├── extraction.py           # Jobs, inspection, understanding, schema inference, conflicts
│   │   │   ├── exports.py              # CSV, JSON, XLSX & research bundles
│   │   │   ├── projects.py             # Research projects CRUD
│   │   │   ├── records.py              # Tabular record editing & audit trails
│   │   │   └── validation.py           # Rule-based validation issue resolution
│   │   ├── llm/                        # Multi-provider LLM core
│   │   │   ├── base.py                 # Abstract LLMProvider interface & token/cost tracker
│   │   │   ├── registry.py             # Model metadata catalog & secure credential vault
│   │   │   ├── router.py               # 8-level escalation router & execution presets
│   │   │   ├── schemas.py              # Pydantic schemas (DocumentMap, SchemaInference, Conflicts)
│   │   │   └── providers/              # Adapters (Ollama, Gemini, Claude, Groq, DeepSeek, OpenAI)
│   │   ├── models/                     # SQLAlchemy models (Project, Document, Dataset, Job, Record, AIConfig, EvaluationRun)
│   │   ├── pipeline/                   # Pipeline orchestrator, Normalizer, Validator, Exporter
│   │   ├── prompts/                    # Versioned modular prompt contracts (v2.0.0)
│   │   ├── services/                   # Specialized intelligence services
│   │   │   ├── document_inspector.py   # PDF layout, text density, continuation table detector
│   │   │   ├── chunk_manager.py        # Table-aware chunking with context overlap & SHA-256 cache
│   │   │   ├── reconciliation_engine.py# Cross-model reconciliation & conflict generator
│   │   │   ├── evaluation_engine.py    # Precision, Recall, F1 & Field Accuracy evaluator
│   │   │   └── manifest_generator.py   # Research bundle generator (dictionary, provenance, manifest)
│   │   ├── database.py                 # SQLite/Postgres dual-engine with dynamic schema sync
│   │   └── main.py                     # FastAPI app entry point & CORS
│   └── run.py                          # Backend standalone runner
│
├── frontend/                           # Vite + React 18 + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/                 # UI components, Layout, Sidebar, SourceDocumentModal
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx           # Workstation telemetry, KPIs & activity history
│   │   │   ├── Projects.tsx            # Project workspace management
│   │   │   ├── Documents.tsx           # Document ingestion, classification & PDF preview
│   │   │   ├── AiModels.tsx            # Provider setup, credential vault & connection testing
│   │   │   ├── Pipeline.tsx            # 4-stage intelligent extraction wizard & live queue
│   │   │   ├── Datasets.tsx            # Datasets catalogue
│   │   │   ├── DatasetDetails.tsx      # Record browser, Data Dictionary tab & sign-off modal
│   │   │   ├── Validation.tsx          # Rule verification & inline exception resolution
│   │   │   ├── Review.tsx              # Multi-model discrepancy queue & audit trail
│   │   │   ├── Evaluation.tsx          # Golden dataset benchmark dashboard
│   │   │   └── Exports.tsx             # Multi-format exporter & research bundles
│   │   ├── services/api.ts             # Strongly-typed Axios API client
│   │   ├── store/useAppStore.ts        # Zustand global state (project context, source modal)
│   │   └── types/index.ts              # TypeScript domain types & interfaces
│   └── package.json
│
├── storage/                            # Storage directory (gitignored files)
│   ├── uploads/                        # Ingested source PDFs
│   ├── exports/                        # Generated exports & research bundles
│   └── dataforge.db                    # SQLite primary/fallback database
│
├── tests/                              # Automated test suite (46 passed)
│   ├── test_api_v1.py                  # API endpoints integration tests
│   ├── test_document_intelligence.py   # PDF layout inspection & table detection
│   ├── test_llm_system.py              # LLM registry, providers & credential resolution
│   ├── test_reconciliation_and_golden.py # Cross-model reconciliation & benchmark metrics
│   └── test_pipeline_e2e.py            # Full end-to-end extraction job test
│
├── run_dev.py                          # Root dev server launcher
├── start.bat                           # Windows one-click dual launcher (backend + frontend)
└── .env.example                        # Environment variable configuration template
```

---

## 5. Quick Start Guide

### Option A: One-Click Windows Launcher (Recommended)
Double-click **`start.bat`** in the project root. This spawns both the FastAPI backend on port `8000` and the Vite frontend on port `5173` in separate terminal windows.

### Option B: Manual Terminal Execution

#### 1. Backend Server
```powershell
# In the project root (using the virtual environment):
python run_dev.py
```
*Backend runs at `http://127.0.0.1:8000` with interactive Swagger API docs at `http://127.0.0.1:8000/docs`.*

#### 2. Frontend Workstation
```powershell
cd frontend
npm run dev
```
*Open `http://localhost:5173` in your browser.*

---

## 6. Configuring API Keys

You have two convenient options:

1. **Through the Web UI (Instant & Recommended)**:
   - Navigate to **[AI Models & LLMs](http://localhost:5173/ai-models)** (`/ai-models`).
   - Enter your key under the desired provider (e.g., DeepSeek, Claude, Gemini, Groq, OpenAI).
   - Click **Save Key**, then click **Test Connection** to verify latency.
2. **Through the `.env` File**:
   - Copy `.env.example` to `.env` in the project root:
     ```env
     DEEPSEEK_API_KEY=sk-...
     ANTHROPIC_API_KEY=sk-ant-...
     GEMINI_API_KEY=AIzaSy...
     GROQ_API_KEY=gsk_...
     OPENAI_API_KEY=sk-...
     OLLAMA_BASE_URL=http://localhost:11434
     ```
   - Restart the backend to load the environment variables.

---

## 7. The Standard Research Export Bundle

When an extraction job completes, clicking **Export Bundle** downloads a complete, publication-ready research package:

| File | Purpose |
| :--- | :--- |
| **`dataset.csv` / `.xlsx` / `.json`** | Clean, validated tabular dataset ready for Stata, R, Python, or SQL databases. |
| **`data_dictionary.csv`** | Standardized codebook specifying column names, original source headers, data types, nullability, primary key flags, and semantic descriptions. |
| **`provenance.csv`** | Row-by-row audit trail linking every record to its document ID, source page number (`#page=N`), and extraction model. |
| **`extraction_manifest.json`** | Cryptographic SHA-256 hash, timestamps, model metadata, prompt versions, and pipeline parameters for scientific reproducibility. |

---

## 8. Golden Dataset Benchmark Evaluation

Under **Evaluation Benchmarks** (`/evaluation`), researchers can benchmark any extraction against a verified ground truth CSV/JSON to compute:
- **Record Recall**: Percentage of ground truth records successfully captured.
- **Record Precision**: Percentage of extracted records that are genuine ground truth entries.
- **Record F1-Score**: Harmonic mean of Precision and Recall.
- **Field Accuracy**: Percentage of matching cell values across all shared columns.
- **Mismatch Table**: Identifies exact field-level discrepancies, missing rows, and phantom rows.

---

## 9. Automated Testing & Verification

Run the full automated test suite:
```powershell
python -m pytest tests/
```
*Result: **46/46 passed** (API v1, Document Intelligence, LLM System, Reconciliation, Golden Benchmarking, E2E Pipeline).*

Build the production frontend:
```powershell
cd frontend
npm run build
```
*Result: **0 TypeScript errors**, compiled in under 30s.*

---

## 10. License & Research Attribution

Internal research data-engineering platform developed for the **Wits–merSETA Darkroom** team. All rights reserved.
