from __future__ import annotations
import json
from typing import Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ManifestDatasetSummary(BaseModel):
    name: str
    record_count: int
    column_count: int
    columns: List[str]
    quality_score: float


class ExtractionManifest(BaseModel):
    project_name: str
    pipeline_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str
    source_documents: List[str] = Field(default_factory=list)
    total_pages_inspected: int = 0
    total_records_extracted: int = 0
    records_valid: int = 0
    records_with_warnings: int = 0
    records_critical: int = 0
    extraction_methods: List[str] = Field(default_factory=list)
    datasets: List[ManifestDatasetSummary] = Field(default_factory=list)
    system_environment: Dict[str, str] = Field(default_factory=dict)
    provenance_enabled: bool = True

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2)
