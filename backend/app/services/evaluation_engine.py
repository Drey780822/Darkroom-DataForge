import uuid
from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Optional
import pandas as pd

from backend.app.llm.schemas import EvaluationReport, FieldMismatchDetail

logger = logging.getLogger("dataforge.services.evaluation_engine")

class EvaluationEngineService:
    """Compares extracted records against Golden Datasets (ground truth) and calculates precision, recall, and field accuracy."""

    @classmethod
    def evaluate(
        cls,
        dataset_id: str,
        golden_df: pd.DataFrame,
        actual_records: List[Dict[str, Any]],
        golden_name: str = "Ground Truth Benchmark",
    ) -> EvaluationReport:
        # Standardize golden columns
        golden_df.columns = [str(c).strip().lower().replace(" ", "_") for c in golden_df.columns]
        expected_records = golden_df.to_dict(orient="records")

        # Determine identifier key
        candidate_id_keys = ["saqa_id", "ofo_code", "occupation_code", "code", "id", "variable", "var_name", "qualification_title", "occupation_title", "title"]
        id_key = None
        for k in candidate_id_keys:
            if k in golden_df.columns:
                id_key = k
                break

        # Map expected records by identifier or row index
        expected_map = {}
        for idx, rec in enumerate(expected_records):
            val = str(rec.get(id_key, "")).strip().lower() if id_key else str(idx)
            if val:
                expected_map[val] = rec

        actual_map = {}
        for idx, rec in enumerate(actual_records):
            val = str(rec.get(id_key, "")).strip().lower() if id_key else str(idx)
            if val:
                actual_map[val] = rec

        matched_keys = set(expected_map.keys()).intersection(set(actual_map.keys()))
        missing_keys = set(expected_map.keys()) - set(actual_map.keys())
        extra_keys = set(actual_map.keys()) - set(expected_map.keys())

        # Field-level comparison across matched records
        mismatches: List[FieldMismatchDetail] = []
        total_fields_evaluated = 0
        matching_fields_count = 0

        row_idx = 0
        for k in matched_keys:
            row_idx += 1
            exp_row = expected_map[k]
            act_row = actual_map[k]

            common_cols = set(exp_row.keys()).intersection(set(act_row.keys()))
            for col in common_cols:
                if col.startswith("_") or col in ["source_page", "confidence", "issues", "field_provenance"]:
                    continue

                exp_val = exp_row.get(col)
                act_val = act_row.get(col)

                total_fields_evaluated += 1
                str_exp = str(exp_val).strip().lower() if exp_val is not None else ""
                str_act = str(act_val).strip().lower() if act_val is not None else ""

                if str_exp == str_act:
                    matching_fields_count += 1
                else:
                    mismatches.append(
                        FieldMismatchDetail(
                            row_index=row_idx,
                            field_name=col,
                            expected_value=exp_val,
                            actual_value=act_val,
                            identifier_value=k,
                        )
                    )

        total_expected = len(expected_records)
        total_actual = len(actual_records)
        matched_count = len(matched_keys)
        missing_count = len(missing_keys)
        extra_count = len(extra_keys)

        # Precision, Recall, F1
        recall = round((matched_count / max(1, total_expected)) * 100, 2)
        precision = round((matched_count / max(1, total_actual)) * 100, 2)
        f1 = round((2 * precision * recall / max(0.001, precision + recall)), 2)
        field_accuracy = (
            round((matching_fields_count / max(1, total_fields_evaluated)) * 100, 2)
            if total_fields_evaluated > 0
            else 100.0
        )

        missing_samples = [expected_map[k] for k in list(missing_keys)[:10]]
        extra_samples = [actual_map[k] for k in list(extra_keys)[:10]]

        return EvaluationReport(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            golden_dataset_name=golden_name,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            total_expected_records=total_expected,
            total_actual_records=total_actual,
            matched_records_count=matched_count,
            missing_records_count=missing_count,
            extra_records_count=extra_count,
            field_mismatches_count=len(mismatches),
            record_recall=recall,
            record_precision=precision,
            record_f1_score=f1,
            field_accuracy=field_accuracy,
            mismatches=mismatches[:100],
            missing_record_samples=missing_samples,
            extra_record_samples=extra_samples,
        )
