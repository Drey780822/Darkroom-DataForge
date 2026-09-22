from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ReviewAuditCreate(BaseModel):
    record_id: str
    action: str  # edit_field, approve_record, reject_record, flag_record
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    reviewed_by: Optional[str] = "Researcher"

class ReviewAuditResponse(BaseModel):
    id: str
    dataset_id: str
    record_id: str
    action: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    reviewed_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReviewRequiredResponse(BaseModel):
    id: int
    job_id: Optional[str] = None
    document_id: Optional[str] = None
    dataset_id: Optional[str] = None
    original_value: str
    issue: str
    source_page: str
    reason: str
    agreement_score: Optional[float] = None
    resolved: bool
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ReviewRequiredResolveRequest(BaseModel):
    resolved_by: Optional[str] = "Researcher"
    correction: Optional[str] = None
