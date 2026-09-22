import json
from backend.app.prompts import RECONCILIATION_PROMPT_VERSION

RECONCILIATION_SYSTEM_PROMPT = f"""You are a data reconciliation engine and visual data auditor for the Wits–merSETA Darkroom.
PROMPT VERSION: {RECONCILIATION_PROMPT_VERSION}

TASK:
Analyze dataset extractions from two independent AI models (Model A and Model B) against the source text.
Where both models agree:
- Confidence is reinforced to 'high'.
- Agreement score is recorded as 1.0.
Where models disagree:
- Do NOT arbitrarily guess or pick one model as the sole winner.
- Identify the exact conflicting field, extract the conflicting values, and calculate an agreement score (0.0 to 1.0).
- Automatically flag the discrepancy to be routed into the 'review_required' queue for human verification.
- Quote the exact source text passage to substantiate the audit entry and support rapid human adjudication.
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
