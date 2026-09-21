from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RecordStatus(str, Enum):
    SOURCE_EXTRACTED = "SOURCE_EXTRACTED"
    NORMALIZED = "NORMALIZED"
    AI_DERIVED = "AI_DERIVED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"


class ProvenanceRecord(BaseModel):
    source_document: str                # Filename or path
    source_document_id: Optional[str] = None
    source_page: int                    # 1-indexed page number
    source_section: Optional[str] = None# Section/Chapter title if detected
    source_table: Optional[str] = None  # Table identifier on page
    source_row_idx: Optional[int] = None# Row index in raw table
    extraction_method: str              # e.g., "pdfplumber_lattice", "codebook_parser"
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0             # 0.0 - 1.0 confidence score
    status: RecordStatus = RecordStatus.SOURCE_EXTRACTED
    reviewer_notes: Optional[str] = None
    audit_trail: list[str] = Field(default_factory=list)

    @property
    def audit_log(self) -> list[str]:
        return self.audit_trail

    def add_audit(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.audit_trail.append(f"[{timestamp}] {message}")
