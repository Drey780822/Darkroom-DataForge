from __future__ import annotations
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .provenance import ProvenanceRecord, RecordStatus


class CellValue(BaseModel):
    raw_value: Any
    normalized_value: Any
    is_modified: bool = False
    confidence: float = 1.0
    field_name: str
    error_message: Optional[str] = None


class Record(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cells: Dict[str, CellValue] = Field(default_factory=dict)
    provenance: ProvenanceRecord
    is_flagged_for_review: bool = False
    review_dismissed: bool = False

    def get_value(self, field_name: str, prefer_normalized: bool = True) -> Any:
        cell = self.cells.get(field_name)
        if not cell:
            return None
        return cell.normalized_value if prefer_normalized else cell.raw_value

    def set_value(self, field_name: str, raw_value: Any, normalized_value: Any, confidence: float = 1.0) -> None:
        is_mod = (str(raw_value).strip() != str(normalized_value).strip())
        self.cells[field_name] = CellValue(
            field_name=field_name,
            raw_value=raw_value,
            normalized_value=normalized_value,
            is_modified=is_mod,
            confidence=confidence
        )

    def to_dict(self, prefer_normalized: bool = True, include_provenance: bool = False) -> Dict[str, Any]:
        data = {k: self.get_value(k, prefer_normalized=prefer_normalized) for k in self.cells.keys()}
        if include_provenance:
            data["_source_document"] = self.provenance.source_document
            data["_source_page"] = self.provenance.source_page
            data["_extraction_method"] = self.provenance.extraction_method
            data["_confidence"] = self.provenance.confidence
            data["_status"] = self.provenance.status.value
        return data

    def to_raw_dict(self) -> Dict[str, Any]:
        return {k: v.raw_value for k, v in self.cells.items()}
