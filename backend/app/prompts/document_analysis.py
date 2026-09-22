from backend.app.prompts import DOCUMENT_ANALYSIS_PROMPT_VERSION

DOCUMENT_ANALYSIS_SYSTEM_PROMPT = f"""You are a senior document intelligence engineer for the Wits–merSETA Darkroom research team.
Your task is to analyze the structural topology and informational purpose of this South African research document.
PROMPT VERSION: {DOCUMENT_ANALYSIS_PROMPT_VERSION}

OBJECTIVE:
Analyze the provided document inspection telemetry and sample page text.
Identify:
1. Document purpose and classified document type (e.g. occupational_dataset, qualifications_list, codebook_survey, technical_report, generic_table).
2. Major logical sections (e.g. Executive Summary, Methodology, Tabular Listings, Annexures).
3. Candidate structured datasets embedded in the document.
4. Continuation tables spanning across multiple pages.
5. Annexures or appendix tables containing secondary datasets.

STRICT RESEARCH CONSTRAINTS:
- Do NOT extract individual data rows in this pass.
- Base your analysis EXCLUSIVELY on the provided document pages and structural signals.
- Return ONLY a valid JSON object matching the requested schema.
"""

def build_document_analysis_user_prompt(
    filename: str,
    page_count: int,
    detected_sections: list,
    detected_tables: list,
    page_samples: list,
) -> str:
    sections_summary = "\n".join([f"- {s.get('title', 'Unknown')} (pp. {s.get('start_page')}-{s.get('end_page')})" for s in detected_sections[:10]]) or "None pre-detected"
    tables_summary = "\n".join([f"- Table p.{t.get('page_number')}: headers={t.get('headers', [])}" for t in detected_tables[:10]]) or "None pre-detected"
    samples_text = "\n\n".join([f"--- PAGE {p.get('page_number')} SAMPLE ---\n{p.get('text_preview', '')[:1200]}" for p in page_samples[:5]])

    return f"""Document Filename: {filename}
Total Page Count: {page_count}

Pre-Detected Structural Signals:
Sections:
{sections_summary}

Sample Detected Tables:
{tables_summary}

Page Text Previews:
{samples_text}

Analyze this document and return the DocumentUnderstandingResponse JSON.
"""
