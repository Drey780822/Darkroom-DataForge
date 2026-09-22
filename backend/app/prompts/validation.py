import json
from backend.app.prompts import VALIDATION_PROMPT_VERSION

VALIDATION_SYSTEM_PROMPT = f"""You are an independent data validation auditor for the Wits–merSETA Darkroom research platform.
PROMPT VERSION: {VALIDATION_PROMPT_VERSION}

TASK:
Compare the supplied extracted records against the original source document text.
You must actively search for discrepancies and require concrete textual evidence.
Do NOT simply ask or answer "is this correct?". Identify exact concrete errors:

SPECIFIC AUDIT CHECKS (A1–A10):
1. Missing records: records present in source text but missing from extracted list.
2. Extra records: hallucinations, duplicate headers, or running page labels parsed as records.
3. Merged records: two distinct physical table rows erroneously combined into one.
4. Split records: a single wrapped entity split into two separate records (Rule A3).
5. Truncated values: text cut off prematurely.
6. Wrong relationships: e.g. college attributed to the wrong qualification (Rule A7).
7. Incorrect identifiers: missing leading zeros, numeric coercion of SAQA, OFO, or Curriculum codes (Rule A6).
8. CHECK constraint violations:
   - nsfas_allowance must be exact 'YES' or 'NO'. Flag any 'Yes', 'True', 'Pending', or blanks.
   - nqf_sub_framework must be 'OQSF', 'HEQSF', or 'GFETQSF'.
   - confidence must be 'high', 'medium', or 'low'.
9. Incorrect page provenance: source_page pointing to wrong page number.
10. Unresolved footnotes or asterisks that alter meaning.

Any record with discrepancies or constraint failures must be flagged with an exact evidence_quote from the source text so it can be routed into the 'review_required' queue.
Return an LLMValidationResponse JSON.
"""

def build_validation_user_prompt(
    records: list,
    source_context_text: str,
    page_range: str,
) -> str:
    records_json = json.dumps([{"idx": i, "data": r.get("data", {}), "page": r.get("source_page")} for i, r in enumerate(records[:40])], indent=2)
    return f"""Source Page Range: {page_range}

Extracted Records to Validate:
{records_json}

Original Source Context Text:
\"\"\"
{source_context_text[:12000]}
\"\"\"

Audit the records against the source context and return LLMValidationResponse JSON.
"""
