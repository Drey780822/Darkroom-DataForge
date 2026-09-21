from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
from models.field import FieldDefinition, DataType
from models.record import Record


class SchemaDetector:
    """Infers database-ready column names, types, nullability, and constraints from extracted tables."""

    @staticmethod
    def to_snake_case(name: str) -> str:
        if not name:
            return "unnamed_column"
        # Strip non-alphanumeric except spaces, underscores, and hyphens
        cleaned = re.sub(r"[^\w\s-]", "", name).strip()
        # Replace hyphens and whitespace with underscore
        cleaned = re.sub(r"[-\s]+", "_", cleaned)
        # Convert CamelCase to snake_case
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", cleaned)
        snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
        # Remove consecutive underscores
        snake = re.sub(r"_+", "_", snake).strip("_")
        return snake or "column"

    @classmethod
    def infer_column_type(cls, values: List[Any]) -> Tuple[DataType, float]:
        non_nulls = [v for v in values if v is not None and str(v).strip() != ""]
        if not non_nulls:
            return DataType.STRING, 0.50

        total = len(non_nulls)
        int_count = 0
        float_count = 0
        bool_count = 0
        list_count = 0

        for v in non_nulls:
            s = str(v).strip()
            if isinstance(v, bool) or s.lower() in ["true", "false", "yes", "no"]:
                bool_count += 1
            elif isinstance(v, int) or (s.lstrip("-").isdigit() and not s.startswith("0") or s == "0"):
                int_count += 1
            elif isinstance(v, float) or re.match(r"^-?\d+\.\d+$", s):
                float_count += 1
            elif ";" in s or "," in s and len(s.split(",")) > 2:
                list_count += 1

        if bool_count / total >= 0.85:
            return DataType.BOOLEAN, bool_count / total
        if int_count / total >= 0.85:
            return DataType.INTEGER, int_count / total
        if (int_count + float_count) / total >= 0.85:
            return DataType.FLOAT, (int_count + float_count) / total
        if list_count / total >= 0.60:
            return DataType.LIST, list_count / total

        return DataType.STRING, 0.95

    @classmethod
    def detect_schema(cls, raw_headers: List[str], records: List[Record]) -> List[FieldDefinition]:
        fields: List[FieldDefinition] = []
        seen_names: Dict[str, int] = {}

        for idx, header in enumerate(raw_headers):
            original = header.strip() if header else f"Column_{idx+1}"
            snake_name = cls.to_snake_case(original)

            # Ensure uniqueness
            if snake_name in seen_names:
                seen_names[snake_name] += 1
                snake_name = f"{snake_name}_{seen_names[snake_name]}"
            else:
                seen_names[snake_name] = 1

            # Extract sample values for this field across records
            col_values = []
            for r in records:
                cell = r.cells.get(snake_name) or r.cells.get(original)
                if cell:
                    col_values.append(cell.normalized_value)

            dtype, type_conf = cls.infer_column_type(col_values)
            null_count = sum(1 for v in col_values if v is None)
            is_required = (null_count == 0 and len(col_values) > 0)

            # Heuristics for primary key
            is_pk = (snake_name in ["id", "saqa_id", "ofo_code", "variable_name"] or "code" in snake_name)

            fields.append(
                FieldDefinition(
                    name=snake_name,
                    display_name=original,
                    data_type=dtype,
                    required=is_required,
                    nullable=not is_required,
                    confidence=round(type_conf, 2),
                    source_header=original,
                    is_primary_key=is_pk,
                )
            )

        return fields
