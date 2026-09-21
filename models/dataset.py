from __future__ import annotations
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import pandas as pd
from .field import FieldDefinition, DataType
from .record import Record


class DatasetQuality(BaseModel):
    overall_score: float = 0.0          # 0 - 100%
    extraction_score: float = 0.0       # 0 - 100%
    completeness_score: float = 0.0     # 0 - 100%
    consistency_score: float = 0.0      # 0 - 100%
    validation_score: float = 0.0       # 0 - 100%
    details: Dict[str, Any] = Field(default_factory=dict)


class DatasetMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                           # Database table name e.g. "qualifications"
    display_name: str                   # Human label e.g. "Occupational Qualifications"
    description: Optional[str] = None
    source_documents: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    quality: Optional[DatasetQuality] = None


class Dataset(BaseModel):
    metadata: DatasetMetadata
    columns: List[FieldDefinition] = Field(default_factory=list)
    records: List[Record] = Field(default_factory=list)
    primary_key: List[str] = Field(default_factory=list)

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def column_names(self) -> List[str]:
        return [col.name for col in self.columns]

    def get_column(self, name: str) -> Optional[FieldDefinition]:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def to_pandas(self, prefer_normalized: bool = True, include_provenance: bool = False) -> pd.DataFrame:
        data = [r.to_dict(prefer_normalized=prefer_normalized, include_provenance=include_provenance) for r in self.records]
        if not data:
            cols = self.column_names
            if include_provenance:
                cols += ["_source_document", "_source_page", "_extraction_method", "_confidence", "_status"]
            return pd.DataFrame(columns=cols)
        return pd.DataFrame(data)

    def to_raw_pandas(self) -> pd.DataFrame:
        data = [r.to_raw_dict() for r in self.records]
        if not data:
            return pd.DataFrame(columns=self.column_names)
        return pd.DataFrame(data)
