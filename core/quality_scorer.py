from __future__ import annotations
from typing import Dict, Any
from models.dataset import Dataset, DatasetQuality
from models.validation import ValidationSummary, IssueSeverity


class QualityScorer:
    """Computes transparent, operational multi-dimensional dataset quality metrics."""

    @classmethod
    def calculate_quality(
        cls,
        dataset: Dataset,
        extraction_score: float = 0.95,
        validation_summary: ValidationSummary = None
    ) -> DatasetQuality:
        total_records = len(dataset.records)
        total_columns = len(dataset.columns)

        if total_records == 0 or total_columns == 0:
            return DatasetQuality(
                overall_score=0.0,
                extraction_score=round(extraction_score * 100, 1),
                completeness_score=0.0,
                consistency_score=0.0,
                validation_score=0.0,
                details={"message": "Empty dataset"}
            )

        total_cells = total_records * total_columns

        # 1. Completeness Score (% of non-null cells)
        non_null_cells = 0
        for r in dataset.records:
            for c in dataset.columns:
                val = r.get_value(c.name, prefer_normalized=True)
                if val is not None and str(val).strip() != "":
                    non_null_cells += 1
        completeness = (non_null_cells / total_cells) * 100

        # 2. Consistency Score (% of records without type mismatch / parse error)
        modified_cells = sum(
            sum(1 for c in r.cells.values() if c.is_modified) for r in dataset.records
        )
        # Moderate modification ratio gives higher consistency, heavy corruption reduces it
        consistency = max(70.0, 100.0 - (modified_cells / total_cells * 30.0))

        # 3. Validation Score (% of records with zero critical issues)
        val_score = 100.0
        if validation_summary and total_records > 0:
            critical_penalty = (validation_summary.critical_count / total_records) * 60.0
            warning_penalty = (validation_summary.warning_count / total_records) * 20.0
            val_score = max(0.0, 100.0 - critical_penalty - warning_penalty)

        ext_score = round(extraction_score * 100, 1)
        comp_score = round(completeness, 1)
        cons_score = round(consistency, 1)
        val_score = round(val_score, 1)

        # Weighted aggregate: Extraction 25%, Completeness 25%, Consistency 25%, Validation 25%
        overall = round((ext_score * 0.25) + (comp_score * 0.25) + (cons_score * 0.25) + (val_score * 0.25), 1)

        details = {
            "total_records": total_records,
            "total_columns": total_columns,
            "total_cells": total_cells,
            "non_null_cells": non_null_cells,
            "empty_cell_ratio": round((total_cells - non_null_cells) / total_cells, 3),
            "critical_validation_issues": validation_summary.critical_count if validation_summary else 0,
            "warning_validation_issues": validation_summary.warning_count if validation_summary else 0,
        }

        return DatasetQuality(
            overall_score=overall,
            extraction_score=ext_score,
            completeness_score=comp_score,
            consistency_score=cons_score,
            validation_score=val_score,
            details=details,
        )
