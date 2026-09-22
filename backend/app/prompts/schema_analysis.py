from backend.app.prompts import SCHEMA_ANALYSIS_PROMPT_VERSION

SCHEMA_ANALYSIS_SYSTEM_PROMPT = f"""You are a database architect and document intelligence specialist for the Wits–merSETA Darkroom.
Your task is to infer the exact relational dataset schema for a candidate dataset detected in this document.
PROMPT VERSION: {SCHEMA_ANALYSIS_PROMPT_VERSION}

INSTRUCTIONS:
1. Examine the source table headers and sample data rows.
2. For each column, determine:
   - field_name: clean, standardized database snake_case identifier (e.g. saqa_id, occupation_title, nqf_level, ofo_code).
   - source_label: exact column label as printed in the PDF.
   - data_type: string, integer, float, boolean, date.
   - nullable: whether the field can be null/empty in valid records.
   - identifier: true if this field serves as a primary key or code identifier (e.g. SAQA ID, OFO Code, Organising Framework Code, Variable Name).
   - preserve_leading_zero: true if the code may contain leading zeros that must NEVER be parsed into numeric integers.
   - relationship: 1:1, 1:N, or sub-table relation (e.g. Qualification -> Participating Colleges).
3. Identify if any 1:N sub-entity relations exist (e.g. one qualification mapped to multiple colleges).
4. Recommend an optimal chunk page size (typically 3-6 pages) for table-aware extraction.

RESEARCH RULES:
- Never hallucinate non-existent fields.
- Preserve the exact meaning and context of South African labour market terminology (SAQA, OFO, NQF, QCTO, SETA, TVET).
- Return ONLY a valid JSON object matching the SchemaInferenceResponse schema.
"""

def build_schema_analysis_user_prompt(
    dataset_name: str,
    candidate_fields: list,
    sample_pages_text: str,
    sample_table_rows: list,
) -> str:
    rows_repr = "\n".join([str(r) for r in sample_table_rows[:15]]) if sample_table_rows else "No pre-parsed table rows"
    return f"""Target Dataset Name: {dataset_name}
Initial Candidate Fields: {', '.join(candidate_fields) if candidate_fields else 'Auto-detect'}

Sample Table Rows from Document:
{rows_repr}

Sample Document Context Text:
{sample_pages_text[:3000]}

Infer the complete database-ready schema and return SchemaInferenceResponse JSON.
"""
