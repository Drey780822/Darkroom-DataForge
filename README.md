# DARKROOM DATAFORGE
### Wits–merSETA Darkroom Structured Data Extraction, Validation & Dataset Generation Platform

![Platform](https://img.shields.io/badge/Platform-PySide6%20Desktop-1D3557?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%20--%203.13-D4AF37?style=flat-square)
![Database-Ready](https://img.shields.io/badge/Output-PostgreSQL%20%7C%20Supabase%20%7C%20CSV-22C55E?style=flat-square)

---

## 1. Overview & Purpose

**Darkroom DataForge** is an internal research-grade desktop data engineering and document intelligence workstation built specifically for the **Wits–merSETA Darkroom** team.

The platform transforms complex collections of semi-structured PDF documents—such as **South African Quarterly Labour Force Survey (QLFS) codebooks**, **Public TVET College Occupational Qualifications lists**, **Occupations in High Demand (OIHD) reports**, and technical research annexures—into clean, validated, database-ready machine-readable datasets.

Unlike simplistic "PDF to CSV" converters, Darkroom DataForge implements an end-to-end data engineering pipeline:
- **Zero Blind Trust**: Every cell and record preserves internal provenance (`source_document`, `source_page`, `extraction_method`, `timestamp`, `confidence`).
- **Archetype Classification**: Automatically determines whether a PDF is a structured table, semi-structured report, codebook, repeated tabular list, or scanned document before selecting an extraction strategy.
- **Table Healing & Reconstruction**: Merges multi-page tables, removes repeated headers across page breaks, and heals wrapped text cells.
- **1:N Relational Normalization**: Decomposes composite fields (e.g., qualifications taught at multiple TVET colleges) into relational parent-child entities (`qualifications.csv` and `qualification_colleges.csv`).
- **Human-in-the-Loop Review**: Low-confidence extractions and schema anomalies are queued for operator inspection with direct, synchronized jumping to the exact source PDF page.
- **Strict Data Integrity**: Original source PDFs and raw extractions are never mutated or overwritten.

---

## 2. System Architecture

The application follows a strictly modular architecture across 6 decoupled layers:

```
darkroom_dataforge/
├── app.py                     # Unified GUI & CLI entry point
├── config/
│   ├── config.yaml            # Engine, OCR, theme, concurrency settings
│   └── profiles/              # Document archetype YAML profiles
├── models/                    # Pydantic data structures (Document, Dataset, Record, Field, Provenance)
├── storage/                   # Portable filesystem workspace manager & JSON state store
├── core/                      # Pipeline, Inspector, Classifier, Reconstructor, Normalizer,
│                              # SchemaDetector, RelationshipDetector, Validator, QualityScorer
├── extractors/                # Specialized table, text, codebook, qualifications & OCR extractors
├── exporters/                 # CSV, JSON, Excel (.xlsx), and PostgreSQL / Supabase DDL exporters
├── gui/                       # PySide6 desktop interface with Darkroom Dark styling
├── demo/                      # Synthetic South African PDF generator & 1-click demo project
├── cli/                       # Command-line companion interface for headless automation
└── tests/                     # Comprehensive automated test suite
```

---

## 3. Installation & Setup

### Prerequisites
- Python 3.10 to 3.13
- Windows, macOS, or Linux

### Quick Setup

```bash
# 1. Clone or navigate to the repository
cd "Darkroom DataForge"

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

> [!NOTE]
> On Windows machines where path length limits are encountered due to deep directories, install into a shortened path junction (e.g., `mklink /J .venv C:\Users\<Username>\.ddf_venv`).

---

## 4. Running the Application

### Desktop GUI (Default)

Launch the interactive PySide6 graphical interface:

```bash
python app.py
```

### CLI Companion (Automation & CI)

Darkroom DataForge includes a full-featured CLI for automated batch pipelines:

```bash
# Inspect and classify a PDF document
python app.py inspect document.pdf

# Process a folder of PDFs into a project workspace
python app.py process ./documents --project ./my_project --format all

# Validate extracted datasets in an existing project
python app.py validate ./my_project

# Export datasets with provenance metadata
python app.py export ./my_project --format sql --provenance
```

---

## 5. End-to-End Workflow

```
PDF Documents
     ↓
1. INGESTION       (Drag & drop single files, batches, or directories)
     ↓
2. INSPECTION      (Detects page counts, text density, image ratio, vector grids)
     ↓
3. CLASSIFY        (Assigns archetype: CODEBOOK, REPEATED_TABULAR, REPORT, SCANNED)
     ↓
4. STRATEGY        (Auto-selects optimal extractor; allows manual operator override)
     ↓
5. EXTRACTION      (pdfplumber, PyMuPDF, layout reconstruction, OCR fallback)
     ↓
6. RECONSTRUCT     (Continues tables across pages, removes duplicate headers, heals lines)
     ↓
7. NORMALIZE       (Standardizes Unicode, whitespace, leading zeros, raw vs norm)
     ↓
8. RELATIONSHIPS   (Decomposes 1:N composite fields into relational tables)
     ↓
9. VALIDATION      (Rule-based checks: required, ranges, regex, types; auto-fix safe errors)
     ↓
10. HUMAN REVIEW   (Inspects low-confidence records with side-by-side PDF canvas jump)
     ↓
11. EXPORT         (Generates database-ready CSV, JSON, Excel, and PostgreSQL DDL)
     ↓
12. MANIFEST       (Outputs auditable manifest.json with run version & stats)
```

---

## 6. One-Click TVET Demo Project

To explore the entire pipeline immediately without providing external documents:
1. Launch `python app.py`.
2. Click **⚡ Load TVET Demo** on the Overview Dashboard.
3. The platform dynamically creates synthetic South African documents:
   - `DHET_TVET_Qualifications_2026.pdf`
   - `StatsSA_QLFS_Codebook_2026.pdf`
   - `DHET_OIHD_National_Report_2024.pdf`
4. The pipeline will automatically execute, decomposing TVET qualifications and college offerings into two normalized datasets:
   - `qualifications.csv`
   - `qualification_colleges.csv`
5. Inspect the generated schema, validation reports, and export to PostgreSQL DDL.

---

## 7. Testing & Verification

Run the automated test suite covering all extractors, reconstruction, normalization, relationships, and export engines:

```bash
pytest tests/ -v
```

All 23+ tests execute hermetically with zero external network dependencies.
