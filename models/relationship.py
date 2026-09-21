from __future__ import annotations
import uuid
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_MANY = "MANY_TO_MANY"
    ONE_TO_ONE = "ONE_TO_ONE"


class Relationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    rel_type: RelationshipType = RelationshipType.ONE_TO_MANY
    parent_dataset: str                 # e.g., "qualifications"
    child_dataset: str                  # e.g., "qualification_colleges"
    parent_key: str                     # e.g., "saqa_id"
    foreign_key: str                    # e.g., "saqa_id"
    description: Optional[str] = None
    is_accepted: bool = True
    confidence: float = 0.95
