from __future__ import annotations
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    LIST = "list"
    JSON = "json"


class FieldDefinition(BaseModel):
    name: str                           # Database-ready snake_case name
    display_name: str                   # Human readable label
    data_type: DataType = DataType.STRING
    required: bool = False
    nullable: bool = True
    unique: bool = False
    regex_pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    confidence: float = 1.0
    source_header: Optional[str] = None # Original PDF header text
    description: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_target: Optional[str] = None # e.g. "qualifications.saqa_id"
