from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ExtractionJobCreate(BaseModel):
    project_id: str
    document_ids: List[str] = Field(..., min_length=1)
    pipeline_type: str = "auto"  # qualifications, occupations, codebook, pdf_tables, auto
    extraction_mode: Optional[str] = "high_accuracy"  # fast, balanced, high_accuracy, maximum_accuracy
    provider: Optional[str] = "deepseek"
    model: Optional[str] = "deepseek-reasoner"
    secondary_model: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    target_dataset_name: Optional[str] = None

class ExtractionJobResponse(BaseModel):
    id: str
    project_id: str
    document_id: str
    dataset_id: Optional[str] = None
    pipeline_type: str
    extraction_mode: Optional[str] = "high_accuracy"
    primary_model: Optional[str] = None
    secondary_model: Optional[str] = None
    provider: Optional[str] = None
    prompt_version: Optional[str] = None
    tokens_used: int = 0
    estimated_cost: float = 0.0
    step_status: Optional[str] = "pending"
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    status: str
    parameters: Dict[str, Any]
    progress: int
    metrics: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResolveConflictRequest(BaseModel):
    conflict_id: str
    resolution: str  # accepted_a, accepted_b, manual_override, rejected
    resolved_value: Optional[Any] = None
    comment: Optional[str] = None
    resolved_by: str = "Researcher"
