import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.models.metadata import ReviewRequired

ALLOWED_NSFAS_ALLOWANCES = {"YES", "NO"}
ALLOWED_CONFIDENCE_LEVELS = {"high", "medium", "low"}
ALLOWED_NQF_SUB_FRAMEWORKS = {"OQSF", "HEQSF", "GFETQSF"}
ALLOWED_COLLEGE_QUALITY_FLAGS = {None, "review_possible_variant"}

class Validator:
    """Rule-based data validation engine enforcing schema constraints and relational integrity."""

    @classmethod
    def validate_record(
        cls,
        data: Dict[str, Any],
        schema_columns: List[Dict[str, Any]],
        row_index: int,
    ) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []

        for col in schema_columns:
            name = col.get("name")
            dtype = col.get("type", "string")
            is_required = col.get("required", False)
            val = data.get(name)

            # 1. Required check
            if is_required and (val is None or str(val).strip() == ""):
                issues.append({
                    "row_index": row_index,
                    "column_name": name,
                    "rule_name": f"required_{name}",
                    "severity": "error",
                    "message": f"Required field '{name}' is missing or empty.",
                    "raw_value": str(val) if val is not None else None,
                })
                continue

            if val is None or str(val).strip() == "":
                continue

            val_str = str(val).strip()

            # 2. SAQA ID pattern check
            if "saqa" in name.lower():
                if not re.match(r"^\d{4,7}$", val_str):
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "saqa_id_format",
                        "severity": "error",
                        "message": f"Invalid SAQA ID '{val_str}'. Expected 4 to 7 numeric digits.",
                        "raw_value": val_str,
                    })

            # 3. OFO Code pattern check
            if "ofo" in name.lower():
                if not re.match(r"^\d{4,6}$", val_str):
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "ofo_code_format",
                        "severity": "error",
                        "message": f"Invalid OFO code '{val_str}'. Expected 4 to 6 numeric digits.",
                        "raw_value": val_str,
                    })

            # 4. NQF Level range check (1 to 10)
            if "nqf" in name.lower() and "sub_framework" not in name.lower():
                try:
                    match = re.search(r"\d+", val_str)
                    if match:
                        nqf_val = int(match.group(0))
                        if not (1 <= nqf_val <= 10):
                            issues.append({
                                "row_index": row_index,
                                "column_name": name,
                                "rule_name": "nqf_level_range",
                                "severity": "error",
                                "message": f"NQF Level {nqf_val} is outside allowed range (1 to 10).",
                                "raw_value": val_str,
                            })
                    else:
                        issues.append({
                            "row_index": row_index,
                            "column_name": name,
                            "rule_name": "nqf_level_numeric",
                            "severity": "warning",
                            "message": f"Could not parse numeric NQF level from '{val_str}'.",
                            "raw_value": val_str,
                        })
                except Exception:
                    pass

            # 5. Type validation
            if dtype == "integer":
                try:
                    int(str(val))
                except ValueError:
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "type_integer",
                        "severity": "warning",
                        "message": f"Value '{val_str}' cannot be parsed as integer.",
                        "raw_value": val_str,
                    })
            elif dtype == "float":
                try:
                    float(str(val))
                except ValueError:
                    issues.append({
                        "row_index": row_index,
                        "column_name": name,
                        "rule_name": "type_float",
                        "severity": "warning",
                        "message": f"Value '{val_str}' cannot be parsed as float.",
                        "raw_value": val_str,
                    })

        return issues

    @classmethod
    def validate_qualification_constraints(
        cls,
        record: Dict[str, Any],
        row_index: int = 1,
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """Strict pre-DB application check against the exact CHECK constraints of the relational schema:
        - nsfas_allowance IN ('YES','NO')
        - confidence IN ('high','medium','low')
        - nqf_sub_framework IN ('OQSF','HEQSF','GFETQSF')
        """
        violations = []

        # 1. nsfas_allowance
        nsfas = record.get("nsfas_allowance")
        if nsfas not in ALLOWED_NSFAS_ALLOWANCES:
            violations.append({
                "row_index": row_index,
                "column_name": "nsfas_allowance",
                "rule_name": "chk_nsfas_allowance",
                "severity": "error",
                "message": f"Value '{nsfas}' violates CHECK (nsfas_allowance IN ('YES','NO')). Must be exact uppercase 'YES' or 'NO'.",
                "raw_value": str(nsfas),
            })

        # 2. confidence
        conf = record.get("confidence")
        if conf not in ALLOWED_CONFIDENCE_LEVELS:
            violations.append({
                "row_index": row_index,
                "column_name": "confidence",
                "rule_name": "chk_confidence",
                "severity": "error",
                "message": f"Value '{conf}' violates CHECK (confidence IN ('high','medium','low')).",
                "raw_value": str(conf),
            })

        # 3. nqf_sub_framework
        sub_fw = record.get("nqf_sub_framework")
        if sub_fw not in ALLOWED_NQF_SUB_FRAMEWORKS:
            violations.append({
                "row_index": row_index,
                "column_name": "nqf_sub_framework",
                "rule_name": "chk_nqf_sub_framework",
                "severity": "error",
                "message": f"Value '{sub_fw}' violates CHECK (nqf_sub_framework IN ('OQSF','HEQSF','GFETQSF')).",
                "raw_value": str(sub_fw),
            })

        # 4. Mandatory primary keys
        saqa_id = record.get("saqa_id")
        if not saqa_id or str(saqa_id).strip() == "":
            violations.append({
                "row_index": row_index,
                "column_name": "saqa_id",
                "rule_name": "pk_saqa_id_required",
                "severity": "error",
                "message": "SAQA ID is required and cannot be empty.",
                "raw_value": str(saqa_id),
            })

        is_valid = len(violations) == 0
        return is_valid, violations

    @classmethod
    def route_to_review_required(
        cls,
        db: Session,
        original_value: str,
        issue: str,
        source_page: str,
        reason: str,
        job_id: Optional[str] = None,
        document_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        agreement_score: Optional[float] = None,
    ) -> ReviewRequired:
        """Appends a rejected or discrepant value into the review_required table."""
        rr = ReviewRequired(
            job_id=job_id,
            document_id=document_id,
            dataset_id=dataset_id,
            original_value=str(original_value),
            issue=issue,
            source_page=str(source_page),
            reason=reason,
            agreement_score=agreement_score,
            resolved=False,
        )
        db.add(rr)
        db.flush()
        return rr

    @classmethod
    def calculate_quality_score(
        cls,
        total_records: int,
        error_count: int,
        warning_count: int
    ) -> float:
        if total_records == 0:
            return 100.0
        # Errors deduct 1.5% per error up to 100%, warnings deduct 0.5%
        penalty = (error_count * 1.5 + warning_count * 0.5) / total_records * 100
        score = max(0.0, min(100.0, 100.0 - penalty))
        return round(score, 1)
