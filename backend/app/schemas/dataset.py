from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ColumnDefinition(BaseModel):
    name: str
    original_name: Optional[str] = None
    type: str = "string"
    required: bool = False
    identifier: Optional[bool] = False
    description: Optional[str] = None

class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    schema_name: Optional[str] = "generic"

class DatasetCreate(DatasetBase):
    project_id: str
    document_id: Optional[str] = None
    schema_columns: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class VerifyDatasetRequest(BaseModel):
    verified_by: str = Field(..., min_length=1)
    verification_notes: Optional[str] = None

class DatasetResponse(DatasetBase):
    id: str
    project_id: str
    document_id: Optional[str] = None
    schema_columns: List[Dict[str, Any]]
    record_count: int
    valid_record_count: int
    warning_record_count: int
    error_record_count: int
    quality_score: float
    status: str
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    verification_notes: Optional[str] = None
    data_dictionary: List[Dict[str, Any]] = Field(default_factory=list)
    document_map: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
