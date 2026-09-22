import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from backend.app.llm.schemas import ConflictRecord, ReconciliationResult

logger = logging.getLogger("dataforge.services.reconciliation_engine")

class ReconciliationEngineService:
    """Reconciles extraction outputs from Model A and Model B, computing agreement rates and tagging conflicts."""

    @classmethod
    def _find_identifier(cls, record: Dict[str, Any]) -> Optional[str]:
        """Detect identifier field value if present."""
        for id_field in ["saqa_id", "ofo_code", "occupation_code", "code", "id", "variable", "var_name"]:
            val = record.get(id_field)
            if val:
                return str(val).strip().lower()
        # Fallback to qualification or occupation title
        for title_field in ["qualification_title", "qualification_name", "occupation_title", "title", "name"]:
            val = record.get(title_field)
            if val:
                return str(val).strip().lower()
        return None

    @classmethod
    def reconcile(
        cls,
        records_a: List[Dict[str, Any]],
        records_b: List[Dict[str, Any]],
        model_a_name: str,
        model_b_name: str,
    ) -> ReconciliationResult:
        if not records_a and not records_b:
            return ReconciliationResult(
                total_records_a=0,
                total_records_b=0,
                matched_records=0,
                agreement_rate=100.0,
                conflicts=[],
                reconciled_records=[],
            )

        if not records_b:
            # Only Model A was run
            return ReconciliationResult(
                total_records_a=len(records_a),
                total_records_b=0,
                matched_records=len(records_a),
                agreement_rate=100.0,
                conflicts=[],
                reconciled_records=records_a,
            )

        # Index Model B records by identifier
        b_by_id = {}
        for b_rec in records_b:
            ident = cls._find_identifier(b_rec)
            if ident:
                b_by_id[ident] = b_rec

        conflicts: List[ConflictRecord] = []
        reconciled_records: List[Dict[str, Any]] = []

        total_fields_compared = 0
        matching_fields_count = 0
        matched_records_count = 0

        for idx, a_rec in enumerate(records_a):
            ident = cls._find_identifier(a_rec)
            b_rec = b_by_id.get(ident) if ident else None

            if b_rec:
                matched_records_count += 1
                merged_data = dict(a_rec)
                page = a_rec.get("source_page", b_rec.get("source_page", 1))

                # Compare fields
                all_keys = set(a_rec.keys()).union(set(b_rec.keys()))
                for k in all_keys:
                    if k.startswith("_") or k in ["source_page", "confidence", "issues", "field_provenance"]:
                        continue

                    val_a = a_rec.get(k)
                    val_b = b_rec.get(k)

                    total_fields_compared += 1
                    # Normalize comparison (strings, whitespace, casing)
                    str_a = str(val_a).strip().lower() if val_a is not None else ""
                    str_b = str(val_b).strip().lower() if val_b is not None else ""

                    if str_a == str_b:
                        matching_fields_count += 1
                        merged_data[k] = val_a if val_a is not None else val_b
                    else:
                        # Conflict detected! Do not arbitrarily pick.
                        conflict = ConflictRecord(
                            id=str(uuid.uuid4()),
                            row_index=idx + 1,
                            field_name=k,
                            value_a=val_a,
                            value_b=val_b,
                            source_page=page,
                            model_a=model_a_name,
                            model_b=model_b_name,
                            resolution="requires_review",
                        )
                        conflicts.append(conflict)
                        merged_data[k] = val_a  # Default to Model A but flag
                        merged_data[f"__conflict_{k}"] = True

                reconciled_records.append(merged_data)
            else:
                # In A but not in B
                reconciled_records.append(a_rec)

        # Calculate agreement rate
        agreement_rate = (
            round((matching_fields_count / max(1, total_fields_compared)) * 100, 2)
            if total_fields_compared > 0
            else 100.0
        )

        return ReconciliationResult(
            total_records_a=len(records_a),
            total_records_b=len(records_b),
            matched_records=matched_records_count,
            agreement_rate=agreement_rate,
            conflicts=conflicts,
            reconciled_records=reconciled_records,
        )
