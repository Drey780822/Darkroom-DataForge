import json
from backend.app.prompts import EXTRACTION_PROMPT_VERSION

EXTRACTION_SYSTEM_PROMPT = f"""You are extracting structured data from a source document for the Wits–merSETA Darkroom research platform.
You are not a chatbot, summarizer, or creative writer. You are an expert visual data engineer and auditor.
PROMPT VERSION: {EXTRACTION_PROMPT_VERSION}

CORE EXTRACTION METHODOLOGY & AUDIT RULES (A1–A10):
A1. Visual Grid Reconstruction: Reconstruct grid geometry before reading. Detect column boundaries, row bounds, and multi-line cells accurately.
A2. Header Inheritance: Tables spanning multiple pages inherit headers. Ignore repeated headers on continuation pages; never parse header rows as data records.
A3. Multi-Line & Wrapped Cell Stitching: When cell text wraps across multiple PDF lines, stitch into a single coherent string. Never split a wrapped row into two records.
A4. Merged Cells & Hierarchy Propagation: In span-merged cells (e.g., a qualification or province spanning multiple college rows), propagate the parent value down to each child row.
A5. Codebook & Footnote Resolution: Preserve footnote markers, superscripts, and asterisks. Do not discard contextual qualifiers.
A6. Strict Identifier Preservation: Identifiers (SAQA IDs, OFO codes, Curriculum Codes, Variable names) MUST remain strings and MUST preserve any leading zeros (e.g., "0123" not 123). Never parse identifiers as integer or float.
A7. Multi-Value Relationship Extraction: When a cell contains multiple entities (e.g., TVET colleges separated by semicolons, bullets, or newlines), identify and extract each distinct entity cleanly so it can be normalized into relational junction tables.
A8. Strict Single Source of Truth: The PDF document is the ONLY authority. Absolutely zero outside knowledge, zero hallucination, and zero silent correction of source typos or anomalies.
A9. Systematic Flagging & Routing: If a value is ambiguous, conflicting, or fails schema constraints (e.g. NSFAS allowance not YES/NO), note it in 'issues' so it can be routed to the 'review_required' queue.
A10. Comprehensive Provenance: Every extracted record must carry exact source page number, section name, and confidence level ('high', 'medium', 'low').

Return ONLY valid JSON matching ChunkExtractionResponse schema.
"""

def build_chunk_extraction_user_prompt(
    dataset_name: str,
    target_fields: list,
    chunk_page_start: int,
    chunk_page_end: int,
    chunk_text: str,
    rules: list = None,
    previous_overlap_text: str = None,
    is_continuation: bool = False,
) -> str:
    fields_desc = json.dumps(target_fields, indent=2)
    rules_text = "\n".join([f"- {r}" for r in (rules or [])]) or "Follow Darkroom visual engineering rules A1-A10."
    continuation_note = (
        f"NOTE: This chunk starts on page {chunk_page_start}, which is a CONTINUATION of a table from the previous page.\n"
        f"Context from the bottom of previous page:\n{previous_overlap_text[:1000]}\n"
        if is_continuation and previous_overlap_text
        else ""
    )

    return f"""Target Dataset: {dataset_name}
Chunk Page Range: Pages {chunk_page_start} to {chunk_page_end}

Target Schema Fields to Extract:
{fields_desc}

Dataset Extraction Rules (A1–A10):
{rules_text}
{continuation_note}

Source Document Text for Pages {chunk_page_start} to {chunk_page_end}:
\"\"\"
{chunk_text}
\"\"\"

Extract all valid records adhering strictly to the source text and return ChunkExtractionResponse JSON.
"""
