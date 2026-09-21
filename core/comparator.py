from __future__ import annotations
from typing import Dict, Any, List, Set, Optional
from pydantic import BaseModel, Field
from models.dataset import Dataset
from models.record import Record


class RecordDiff(BaseModel):
    key: str
    diff_type: str  # "ADDED", "REMOVED", "MODIFIED"
    old_values: Dict[str, Any] = Field(default_factory=dict)
    new_values: Dict[str, Any] = Field(default_factory=dict)
    changed_fields: List[str] = Field(default_factory=list)


class DatasetComparisonReport(BaseModel):
    old_dataset_name: str
    new_dataset_name: str
    key_field: str
    added_count: int = 0
    removed_count: int = 0
    modified_count: int = 0
    unchanged_count: int = 0
    added_records: List[RecordDiff] = Field(default_factory=list)
    removed_records: List[RecordDiff] = Field(default_factory=list)
    modified_records: List[RecordDiff] = Field(default_factory=list)
    new_columns: List[str] = Field(default_factory=list)
    removed_columns: List[str] = Field(default_factory=list)


class DatasetComparator:
    """Compares datasets across processing runs or document editions (e.g. 2024 OIHD vs 2025 OIHD)."""

    @classmethod
    def compare(
        cls,
        old_dataset: Dataset,
        new_dataset: Dataset,
        key_field: Optional[str] = None
    ) -> DatasetComparisonReport:
        # Determine comparison key (use primary key or first column)
        pk = key_field
        if not pk:
            if old_dataset.primary_key:
                pk = old_dataset.primary_key[0]
            elif old_dataset.columns:
                pk = old_dataset.columns[0].name
            else:
                pk = "id"

        old_cols = set(old_dataset.column_names)
        new_cols = set(new_dataset.column_names)
        new_columns = sorted(list(new_cols - old_cols))
        removed_columns = sorted(list(old_cols - new_cols))

        old_map: Dict[str, Record] = {}
        for r in old_dataset.records:
            val = str(r.get_value(pk, prefer_normalized=True) or "").strip()
            if val:
                old_map[val] = r

        new_map: Dict[str, Record] = {}
        for r in new_dataset.records:
            val = str(r.get_value(pk, prefer_normalized=True) or "").strip()
            if val:
                new_map[val] = r

        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())

        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        added_diffs: List[RecordDiff] = [
            RecordDiff(
                key=k,
                diff_type="ADDED",
                new_values=new_map[k].to_dict(),
            ) for k in sorted(added_keys)
        ]

        removed_diffs: List[RecordDiff] = [
            RecordDiff(
                key=k,
                diff_type="REMOVED",
                old_values=old_map[k].to_dict(),
            ) for k in sorted(removed_keys)
        ]

        modified_diffs: List[RecordDiff] = []
        unchanged_count = 0

        common_cols = old_cols & new_cols

        for k in sorted(common_keys):
            old_r = old_map[k]
            new_r = new_map[k]
            changed_fields = []

            for col in common_cols:
                v1 = str(old_r.get_value(col, prefer_normalized=True) or "").strip()
                v2 = str(new_r.get_value(col, prefer_normalized=True) or "").strip()
                if v1 != v2:
                    changed_fields.append(col)

            if changed_fields:
                modified_diffs.append(
                    RecordDiff(
                        key=k,
                        diff_type="MODIFIED",
                        old_values={c: old_r.get_value(c) for c in changed_fields},
                        new_values={c: new_r.get_value(c) for c in changed_fields},
                        changed_fields=changed_fields,
                    )
                )
            else:
                unchanged_count += 1

        return DatasetComparisonReport(
            old_dataset_name=old_dataset.metadata.name,
            new_dataset_name=new_dataset.metadata.name,
            key_field=pk,
            added_count=len(added_diffs),
            removed_count=len(removed_diffs),
            modified_count=len(modified_diffs),
            unchanged_count=unchanged_count,
            added_records=added_diffs,
            removed_records=removed_diffs,
            modified_records=modified_diffs,
            new_columns=new_columns,
            removed_columns=removed_columns,
        )
