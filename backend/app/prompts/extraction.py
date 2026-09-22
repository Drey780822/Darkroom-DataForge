import json
from backend.app.prompts import EXTRACTION_PROMPT_VERSION

EXTRACTION_SYSTEM_PROMPT = f"""You are extracting structured data from a source document for the Wits–merSETA Darkroom research platform.
PROMPT VERSION: {EXTRACTION_PROMPT_VERSION}

CRITICAL RULES:
1. The source document is the ONLY authority.
2. Extract every valid record belonging to the specified dataset in this chunk.
3. Do not summarize.
4. Do not omit records.
5. Do not invent values.
6. Do not use outside knowledge.
7. Do not correct source information or typos present in the document.
8. Preserve source meaning and original terminology.
9. Reconstruct rows that are split across physical lines into ONE single coherent record.
10. Reconstruct tables that continue across pages.
11. Ignore repeated headers on continuation pages; do NOT turn headers into records.
12. Ignore page numbers, running headers, and running footers.
13. Ignore decorative text, watermarks, and logos.
14. If a value cannot be confidently determined from the source text, set the field to null and add a note in 'issues'.
15. Identifiers (e.g. SAQA IDs, OFO codes, Variable codes) MUST remain strings and MUST preserve any leading zeros.
16. Every record must contain source provenance (source_page, confidence, issues).
17. Return ONLY the required structured schema in valid JSON format.
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
    rules_text = "\n".join([f"- {r}" for r in (rules or [])]) or "Follow default Darkroom extraction rules."
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

Dataset Extraction Rules:
{rules_text}
{continuation_note}

Source Document Text for Pages {chunk_page_start} to {chunk_page_end}:
\"\"\"
{chunk_text}
\"\"\"

Extract all valid records adhering strictly to the source text and return ChunkExtractionResponse JSON.
"""
