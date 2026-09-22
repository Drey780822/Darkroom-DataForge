import json
from backend.app.prompts import RECONCILIATION_PROMPT_VERSION

RECONCILIATION_SYSTEM_PROMPT = f"""You are a data reconciliation engine for the Wits–merSETA Darkroom.
PROMPT VERSION: {RECONCILIATION_PROMPT_VERSION}

TASK:
Analyze dataset extractions from two independent AI models (Model A and Model B) against the source text.
Where both models agree:
- Confidence is reinforced.
Where models disagree:
- Do NOT arbitrarily declare one model the winner.
- Identify the exact conflicting field, quote both values, and flag the record as 'requires_review' for human verification.
- Provide source text quotes where possible to assist the human reviewer.
"""

def build_reconciliation_user_prompt(
    records_a: list,
    records_b: list,
    source_context_text: str,
) -> str:
    sample_a = json.dumps(records_a[:30], indent=2)
    sample_b = json.dumps(records_b[:30], indent=2)
    return f"""Model A Extracted Records:
{sample_a}

Model B Extracted Records:
{sample_b}

Original Document Context:
\"\"\"
{source_context_text[:8000]}
\"\"\"

Reconcile both extractions, identify conflicts, and return ReconciliationResult JSON.
"""
