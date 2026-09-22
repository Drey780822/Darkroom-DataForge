import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# AI Model Configuration & Providers
# ---------------------------------------------------------------------------

class ProviderConfig(BaseModel):
    id: str
    name: str
    description: str
    is_local: bool = False
    is_configured: bool = False
    supports_vision: bool = False
    supports_structured: bool = True
    default_model: str
    available_models: List[str] = Field(default_factory=list)

class ModelMetadata(BaseModel):
    provider: str
    model: str
    display_name: str
    context_window: int = 32000
    supports_json: bool = True
    supports_vision: bool = False
    supports_reasoning: bool = False
    supports_tools: bool = True
    cost_input_per_million: float = 0.0
    cost_output_per_million: float = 0.0

class AIModelConfigSchema(BaseModel):
    id: Optional[str] = None
    name: str
    provider: str  # deepseek, anthropic, google, groq, ollama, openai, openrouter
    model: str
    temperature: float = 0.0
    max_tokens: int = 16000
    reasoning_mode: bool = False
    structured_output: bool = True
    use_vision: str = "auto"  # auto, never, always
    fallback_model: Optional[str] = None
    timeout_seconds: int = 90
    retry_count: int = 3
    is_default: bool = False

class UpdateCredentialsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class TestConnectionRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[int] = None
    provider: str
    model: Optional[str] = None

# ---------------------------------------------------------------------------
# Document Intelligence Map & Understanding
# ---------------------------------------------------------------------------

class PageIntelligence(BaseModel):
    page_number: int
    has_text: bool
    is_scanned: bool = False
    text_density: float = 0.0  # chars / area
    char_count: int = 0
    table_count: int = 0
    image_count: int = 0
    headers_detected: List[str] = Field(default_factory=list)
    footers_detected: List[str] = Field(default_factory=list)

class DetectedSection(BaseModel):
    title: str
    start_page: int
    end_page: int
    section_type: str = "body"  # header, summary, methodology, dataset, annexure, references

class DetectedTable(BaseModel):
    table_id: str
    page_number: int
    start_page: int
    end_page: int
    is_continuation: bool = False
    row_count_estimate: int = 0
    headers: List[str] = Field(default_factory=list)

class DocumentIntelligenceMap(BaseModel):
    document_id: str
    filename: str
    page_count: int
    is_scanned: bool = False
    text_density_avg: float = 0.0
    sections: List[DetectedSection] = Field(default_factory=list)
    tables: List[DetectedTable] = Field(default_factory=list)
    pages: List[PageIntelligence] = Field(default_factory=list)
    continuation_groups: List[List[int]] = Field(default_factory=list)  # groups of page numbers representing contiguous multi-page tables

class DatasetCandidate(BaseModel):
    name: str
    description: str
    pages: List[int]
    candidate_fields: List[str] = Field(default_factory=list)
    table_ids: List[str] = Field(default_factory=list)
    estimated_records: Optional[int] = None

class DocumentUnderstandingResponse(BaseModel):
    document_type: str  # occupational_dataset, qualifications_list, codebook_survey, technical_report, generic_table
    purpose: str
    sections: List[str] = Field(default_factory=list)
    datasets: List[DatasetCandidate] = Field(default_factory=list)
    annexures: List[str] = Field(default_factory=list)
    continuation_tables_found: bool = False
    notes: Optional[str] = None

# ---------------------------------------------------------------------------
# Schema Inference
# ---------------------------------------------------------------------------

class InferredField(BaseModel):
    field_name: str
    source_label: str
    data_type: str = "string"  # string, integer, float, boolean, date, array
    nullable: bool = True
    identifier: bool = False
    description: Optional[str] = None
    relationship: Optional[str] = None  # 1:1, 1:N, foreign_key
    example_value: Optional[str] = None
    preserve_leading_zero: bool = False

class SchemaInferenceResponse(BaseModel):
    dataset_name: str
    description: str
    fields: List[InferredField] = Field(default_factory=list)
    relationships_detected: List[str] = Field(default_factory=list)
    recommended_chunk_size: int = 5  # pages per chunk

# ---------------------------------------------------------------------------
# Structured Extraction Chunk Contract
# ---------------------------------------------------------------------------

class ExtractionChunkContract(BaseModel):
    dataset_name: str
    fields: List[str]
    source_rules: List[str] = Field(default_factory=list)
    is_continuation: bool = False
    previous_page_context: Optional[str] = None
    next_page_context: Optional[str] = None

class FieldProvenance(BaseModel):
    value: Any
    raw_value: Optional[str] = None
    page: int
    bbox: Optional[List[float]] = None
    confidence: float = 1.0

class StructuredRecordItem(BaseModel):
    data: Dict[str, Any]
    raw_data: Optional[Dict[str, Any]] = None
    source_page: int
    end_page: Optional[int] = None
    section: Optional[str] = None
    table_index: Optional[int] = None
    confidence: float = 1.0
    issues: List[str] = Field(default_factory=list)
    field_provenance: Optional[Dict[str, FieldProvenance]] = None

class ChunkExtractionResponse(BaseModel):
    records: List[StructuredRecordItem] = Field(default_factory=list)
    chunk_page_start: int
    chunk_page_end: int
    continuation_table_active: bool = False
    unmapped_rows_count: int = 0
    extraction_notes: Optional[str] = None

# ---------------------------------------------------------------------------
# LLM Validation & Multi-Model Reconciliation
# ---------------------------------------------------------------------------

class LLMValidationIssue(BaseModel):
    record_index: int
    column_name: Optional[str] = None
    severity: str = "warning"  # error, warning, info
    issue_type: str  # missing_record, extra_record, merged_row, split_row, truncated_value, wrong_identifier, source_mismatch
    message: str
    evidence_quote: Optional[str] = None
    source_page: Optional[int] = None

class LLMValidationResponse(BaseModel):
    issues: List[LLMValidationIssue] = Field(default_factory=list)
    verified_record_count: int = 0
    suspect_record_count: int = 0
    summary: str

class ConflictRecord(BaseModel):
    id: Optional[str] = None
    row_index: int
    field_name: str
    value_a: Any
    value_b: Any
    source_page: int
    model_a: str
    model_b: str
    resolution: str = "requires_review"  # requires_review, accepted_a, accepted_b, manual_override, rejected
    resolved_value: Optional[Any] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    comment: Optional[str] = None

class ReconciliationResult(BaseModel):
    total_records_a: int
    total_records_b: int
    matched_records: int
    agreement_rate: float  # 0.0 - 100.0%
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    reconciled_records: List[Dict[str, Any]] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# Evaluation & Golden Dataset
# ---------------------------------------------------------------------------

class FieldMismatchDetail(BaseModel):
    row_index: int
    field_name: str
    expected_value: Any
    actual_value: Any
    identifier_value: Optional[str] = None

class EvaluationReport(BaseModel):
    id: str
    dataset_id: str
    golden_dataset_name: str
    evaluated_at: str
    total_expected_records: int
    total_actual_records: int
    matched_records_count: int
    missing_records_count: int
    extra_records_count: int
    field_mismatches_count: int
    record_recall: float
    record_precision: float
    record_f1_score: float
    field_accuracy: float
    mismatches: List[FieldMismatchDetail] = Field(default_factory=list)
    missing_record_samples: List[Dict[str, Any]] = Field(default_factory=list)
    extra_record_samples: List[Dict[str, Any]] = Field(default_factory=list)
