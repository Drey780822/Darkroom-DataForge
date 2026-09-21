from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class DocumentType(str, Enum):
    STRUCTURED_TABLE = "STRUCTURED_TABLE"
    SEMI_STRUCTURED_REPORT = "SEMI_STRUCTURED_REPORT"
    CODEBOOK_METADATA = "CODEBOOK_METADATA"
    REPEATED_TABULAR = "REPEATED_TABULAR"
    SCANNED_IMAGE = "SCANNED_IMAGE"
    MIXED_DOCUMENT = "MIXED_DOCUMENT"
    UNSUPPORTED_AMBIGUOUS = "UNSUPPORTED_AMBIGUOUS"

    @property
    def label(self) -> str:
        labels = {
            DocumentType.STRUCTURED_TABLE: "Structured Table PDF",
            DocumentType.SEMI_STRUCTURED_REPORT: "Semi-Structured Report",
            DocumentType.CODEBOOK_METADATA: "Codebook / Metadata Guide",
            DocumentType.REPEATED_TABULAR: "Repeated Tabular Document",
            DocumentType.SCANNED_IMAGE: "Scanned / Image PDF",
            DocumentType.MIXED_DOCUMENT: "Mixed Structure PDF",
            DocumentType.UNSUPPORTED_AMBIGUOUS: "Unsupported / Ambiguous",
        }
        return labels.get(self, self.value)


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    INSPECTED = "INSPECTED"
    CLASSIFIED = "CLASSIFIED"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class PageInspection(BaseModel):
    page_number: int
    text_length: int = 0
    word_count: int = 0
    image_count: int = 0
    has_tables: bool = False
    table_count: int = 0
    is_scanned_likely: bool = False
    has_vector_graphics: bool = False
    sample_text: str = ""


class InspectionResult(BaseModel):
    page_count: int = 0
    total_text_length: int = 0
    total_images: int = 0
    scanned_pages_ratio: float = 0.0
    text_availability_score: float = 0.0
    table_likelihood_score: float = 0.0
    has_digital_text: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    pages: List[PageInspection] = Field(default_factory=list)
    inspected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClassificationResult(BaseModel):
    document_type: DocumentType
    confidence: float
    recommended_extractor: str
    reasons: List[str] = Field(default_factory=list)
    alternative_extractors: List[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    id: str
    filename: str
    file_path: str
    file_size_bytes: int
    sha256_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: DocumentStatus = DocumentStatus.PENDING
    inspection: Optional[InspectionResult] = None
    classification: Optional[ClassificationResult] = None
    manual_type_override: Optional[DocumentType] = None
    manual_extractor_override: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def effective_document_type(self) -> Optional[DocumentType]:
        if self.manual_type_override:
            return self.manual_type_override
        if self.classification:
            return self.classification.document_type
        return None

    @property
    def effective_extractor(self) -> Optional[str]:
        if self.manual_extractor_override:
            return self.manual_extractor_override
        if self.classification:
            return self.classification.recommended_extractor
        return "pdf_tables"
