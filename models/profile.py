from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .document import DocumentType


class ProfileColumn(BaseModel):
    name: str
    display_name: str
    type: str = "string"
    required: bool = False
    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[str]] = None
    aliases: List[str] = Field(default_factory=list)
    split_delimiter: Optional[str] = None


class ProfileDataset(BaseModel):
    id: str
    name: str
    primary_key: List[str] = Field(default_factory=list)


class ProfileRelationship(BaseModel):
    name: str
    type: str = "ONE_TO_MANY"
    parent_dataset: str
    child_dataset: str
    foreign_key: str


class ExtractionProfile(BaseModel):
    name: str
    display_name: str
    description: str
    document_type: DocumentType
    recommended_extractor: str
    matching_patterns: Dict[str, Any] = Field(default_factory=dict)
    columns: List[ProfileColumn] = Field(default_factory=list)
    datasets: List[ProfileDataset] = Field(default_factory=list)
    relationships: List[ProfileRelationship] = Field(default_factory=list)
