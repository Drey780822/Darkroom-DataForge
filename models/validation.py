from __future__ import annotations
import uuid
from enum import Enum
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationIssue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    record_id: str
    field_name: Optional[str] = None
    severity: IssueSeverity
    rule_name: str
    message: str
    current_value: Any = None
    suggested_fix: Optional[Any] = None
    is_auto_fixable: bool = False
    is_fixed: bool = False
    source_page: Optional[int] = None
    source_document: Optional[str] = None


class ValidationRule(BaseModel):
    id: str
    name: str
    field_name: str
    rule_type: str  # "required", "type", "regex", "range", "allowed_values", "unique", "referential"
    severity: IssueSeverity = IssueSeverity.WARNING
    parameters: Dict[str, Any] = Field(default_factory=dict)
    custom_message: Optional[str] = None
    is_active: bool = True


class ValidationSummary(BaseModel):
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    total_issues: int = 0
    records_with_issues: int = 0
    auto_fixable_count: int = 0
    issues: List[ValidationIssue] = Field(default_factory=list)
