from __future__ import annotations
import re
from typing import List, Tuple, Optional, Dict, Any
from models.record import Record
from models.dataset import Dataset, DatasetMetadata
from models.field import FieldDefinition, DataType
from models.relationship import Relationship, RelationshipType
from models.provenance import ProvenanceRecord, RecordStatus


class RelationshipDetector:
    """Detects multi-value fields and normalizes 1:N relationships into relational datasets."""

    @classmethod
    def detect_list_column(cls, dataset: Dataset) -> Optional[FieldDefinition]:
        """Finds candidate column containing delimited multiple values (e.g. colleges, categories)."""
        for col in dataset.columns:
            if col.name in ["participating_colleges", "colleges", "institutions", "provinces", "categories"]:
                return col
            # Check values in records
            sample_values = [r.get_value(col.name) for r in dataset.records[:30] if r.get_value(col.name)]
            delimited_count = sum(1 for v in sample_values if isinstance(v, str) and (";" in v or ("," in v and len(v.split(",")) >= 2)))
            if sample_values and (delimited_count / len(sample_values)) >= 0.35:
                return col
        return None

    @classmethod
    def decompose_one_to_many(
        cls,
        parent_dataset: Dataset,
        list_column_name: str,
        child_dataset_name: str,
        child_item_column_name: str,
        parent_pk_column: str,
        delimiter: str = ";"
    ) -> Tuple[Dataset, Dataset, Relationship]:
        """Splits a denormalized dataset into a clean parent entity and a child 1:N relation table."""
        # 1. Clean parent dataset (columns without the list column)
        parent_cols = [c for c in parent_dataset.columns if c.name != list_column_name]
        clean_parent_records: List[Record] = []

        # 2. Child dataset records
        child_cols = [
            FieldDefinition(
                name=parent_pk_column,
                display_name=parent_pk_column.replace("_", " ").title(),
                data_type=DataType.STRING,
                required=True,
                is_foreign_key=True,
                foreign_target=f"{parent_dataset.metadata.name}.{parent_pk_column}",
            ),
            FieldDefinition(
                name=child_item_column_name,
                display_name=child_item_column_name.replace("_", " ").title(),
                data_type=DataType.STRING,
                required=True,
            ),
        ]
        child_records: List[Record] = []

        seen_parent_pks = set()

        for rec in parent_dataset.records:
            pk_val = rec.get_value(parent_pk_column)
            raw_list_val = rec.get_value(list_column_name, prefer_normalized=False)

            # Create clean parent record
            if pk_val not in seen_parent_pks:
                clean_rec = Record(
                    provenance=rec.provenance,
                    is_flagged_for_review=rec.is_flagged_for_review,
                )
                for col in parent_cols:
                    cell = rec.cells.get(col.name)
                    if cell:
                        clean_rec.cells[col.name] = cell
                clean_parent_records.append(clean_rec)
                if pk_val:
                    seen_parent_pks.add(pk_val)

            # Split child items
            if raw_list_val:
                raw_str = str(raw_list_val)
                # Split on semicolon, comma if semicolon absent, or newline
                items = []
                if ";" in raw_str:
                    items = [it.strip() for it in raw_str.split(";") if it.strip()]
                elif "\n" in raw_str:
                    items = [it.strip() for it in raw_str.split("\n") if it.strip()]
                elif "," in raw_str:
                    items = [it.strip() for it in raw_str.split(",") if it.strip()]
                else:
                    items = [raw_str.strip()]

                for item in items:
                    child_rec = Record(
                        provenance=ProvenanceRecord(
                            source_document=rec.provenance.source_document,
                            source_page=rec.provenance.source_page,
                            extraction_method=rec.provenance.extraction_method,
                            confidence=rec.provenance.confidence,
                            status=RecordStatus.NORMALIZED,
                        )
                    )
                    child_rec.set_value(parent_pk_column, pk_val, pk_val)
                    child_rec.set_value(child_item_column_name, item, item)
                    child_records.append(child_rec)

        clean_parent = Dataset(
            metadata=DatasetMetadata(
                name=parent_dataset.metadata.name,
                display_name=parent_dataset.metadata.display_name,
                description=f"Normalized entity: {parent_dataset.metadata.name}",
                source_documents=parent_dataset.metadata.source_documents,
            ),
            columns=parent_cols,
            records=clean_parent_records,
            primary_key=[parent_pk_column],
        )

        child_dataset = Dataset(
            metadata=DatasetMetadata(
                name=child_dataset_name,
                display_name=child_dataset_name.replace("_", " ").title(),
                description=f"Normalized 1:N relation of {parent_dataset.metadata.name}",
                source_documents=parent_dataset.metadata.source_documents,
            ),
            columns=child_cols,
            records=child_records,
            primary_key=[parent_pk_column, child_item_column_name],
        )

        rel = Relationship(
            name=f"{parent_dataset.metadata.name}_to_{child_dataset_name}",
            rel_type=RelationshipType.ONE_TO_MANY,
            parent_dataset=clean_parent.metadata.name,
            child_dataset=child_dataset.metadata.name,
            parent_key=parent_pk_column,
            foreign_key=parent_pk_column,
            description=f"One {parent_dataset.metadata.name} relates to multiple {child_item_column_name} entries",
        )

        return clean_parent, child_dataset, rel
