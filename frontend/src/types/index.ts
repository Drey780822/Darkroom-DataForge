export interface Project {
  id: string;
  name: string;
  description?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  document_count: number;
  dataset_count: number;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  original_name: string;
  file_path: string;
  file_size: number;
  file_hash?: string;
  mime_type: string;
  page_count: number;
  doc_type: 'qualifications' | 'occupations' | 'codebook' | 'general_table' | 'unclassified';
  doc_metadata: Record<string, any>;
  status: 'uploaded' | 'inspected' | 'processing' | 'extracted' | 'failed';
  created_at: string;
  updated_at: string;
}

export interface DocumentInspection {
  id: string;
  filename: string;
  page_count: number;
  doc_type: string;
  doc_metadata: Record<string, any>;
  pages_sample: Array<{
    page_number: number;
    width: number;
    height: number;
    text_preview: string;
    table_count: number;
  }>;
  detected_tables_count: number;
  has_text_layer: boolean;
}

export interface ConflictRecord {
  id?: string;
  row_index: number;
  field_name: string;
  value_a: any;
  value_b: any;
  source_page: number;
  model_a: string;
  model_b: string;
  resolution: 'requires_review' | 'accepted_a' | 'accepted_b' | 'manual_override' | 'rejected';
  resolved_value?: any;
  resolved_by?: string;
  resolved_at?: string;
  comment?: string;
}

export interface ExtractionJob {
  id: string;
  project_id: string;
  document_id: string;
  dataset_id?: string;
  pipeline_type: string;
  extraction_mode?: 'fast' | 'balanced' | 'high_accuracy' | 'maximum_accuracy';
  primary_model?: string;
  secondary_model?: string;
  provider?: string;
  prompt_version?: string;
  tokens_used?: number;
  estimated_cost?: number;
  step_status?: 'pending' | 'inspecting' | 'understanding' | 'inferring_schema' | 'extracting' | 'validating' | 'reconciling' | 'completed' | 'failed';
  conflicts?: ConflictRecord[];
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  parameters: Record<string, any>;
  progress: number;
  metrics: {
    total_documents?: number;
    total_tables?: number;
    records_extracted?: number;
    valid_records?: number;
    errors_count?: number;
    warnings_count?: number;
    quality_score?: number;
    duration_ms?: number;
    tokens_used?: number;
    estimated_cost_usd?: number;
    conflicts_count?: number;
  };
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ColumnDefinition {
  name: string;
  original_name?: string;
  source_label?: string;
  type: 'string' | 'integer' | 'float' | 'boolean' | 'date';
  required: boolean;
  identifier?: boolean;
  description?: string;
}

export interface Dataset {
  id: string;
  project_id: string;
  document_id?: string;
  name: string;
  description?: string;
  schema_name: string;
  schema_columns: ColumnDefinition[];
  record_count: number;
  valid_record_count: number;
  warning_record_count: number;
  error_record_count: number;
  quality_score: number;
  status: 'raw' | 'normalized' | 'validated' | 'reviewed' | 'published';
  is_verified?: boolean;
  verified_by?: string;
  verified_at?: string;
  verification_notes?: string;
  data_dictionary?: Array<{
    dataset_name: string;
    column_name: string;
    source_label: string;
    data_type: string;
    nullable: string;
    description: string;
    identifier: string;
    example_value: string;
    source_pages: string;
  }>;
  document_map?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Provenance {
  document_id?: string;
  document_name?: string;
  page_number?: number;
  table_index?: number;
  bounding_box?: [number, number, number, number];
  method?: string;
  model?: string;
  prompt_version?: string;
}

export interface DatasetRecord {
  id: string;
  dataset_id: string;
  row_index: number;
  data: Record<string, any>;
  raw_data?: Record<string, any>;
  confidence_score: number;
  provenance: Provenance;
  status: 'valid' | 'warning' | 'error' | 'human_reviewed';
  review_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface RecordListResponse {
  total: number;
  page: number;
  page_size: number;
  records: DatasetRecord[];
}

export interface ValidationIssue {
  id: string;
  dataset_id: string;
  record_id?: string;
  row_index?: number;
  column_name?: string;
  rule_name: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  raw_value?: string;
  is_resolved: boolean;
  resolved_by?: string;
  resolution_comment?: string;
  created_at: string;
}

export interface ValidationSummary {
  dataset_id: string;
  quality_score: number;
  total_records: number;
  valid_records: number;
  warning_records: number;
  error_records: number;
  issues_by_severity: {
    error: number;
    warning: number;
    info: number;
  };
  issues_by_column: Record<string, number>;
  issues: ValidationIssue[];
}

export interface ReviewAudit {
  id: string;
  dataset_id: string;
  record_id: string;
  action: 'edit_field' | 'approve_record' | 'reject_record' | 'flag_record' | 'update_record' | 'resolve_issue';
  field_name?: string;
  old_value?: string;
  new_value?: string;
  reason?: string;
  reviewed_by: string;
  created_at: string;
}

export interface ActivityLog {
  id: string;
  project_id?: string;
  entity_type: string;
  entity_id?: string;
  action: string;
  description: string;
  user: string;
  details: Record<string, any>;
  created_at: string;
}

export interface ExportResponse {
  download_url: string;
  filename: string;
  format: string;
  record_count: number;
  file_size_bytes: number;
}

// ---------------------------------------------------------------------------
// AI Model & Provider Types
// ---------------------------------------------------------------------------

export interface ProviderConfig {
  id: string;
  name: string;
  description: string;
  is_local: boolean;
  is_configured: boolean;
  supports_vision: boolean;
  supports_structured: boolean;
  default_model: string;
  available_models: string[];
}

export interface ModelMetadata {
  provider: string;
  model: string;
  display_name: string;
  context_window: number;
  supports_json: boolean;
  supports_vision: boolean;
  supports_reasoning: boolean;
  cost_input_per_million: number;
  cost_output_per_million: number;
}

export interface AIModelConfig {
  id?: string;
  name: string;
  provider: string;
  model: string;
  temperature: number;
  max_tokens: number;
  reasoning_mode: boolean;
  structured_output: boolean;
  use_vision: 'auto' | 'never' | 'always';
  fallback_model?: string;
  timeout_seconds: number;
  retry_count: number;
  is_default: boolean;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  latency_ms?: number;
  provider: string;
  model?: string;
}

export interface DocumentIntelligenceMap {
  document_id: string;
  filename: string;
  page_count: number;
  is_scanned: boolean;
  text_density_avg: number;
  sections: Array<{
    title: string;
    start_page: number;
    end_page: number;
    section_type: string;
  }>;
  tables: Array<{
    table_id: string;
    page_number: number;
    start_page: number;
    end_page: number;
    is_continuation: boolean;
    row_count_estimate: number;
    headers: string[];
  }>;
  pages: Array<{
    page_number: number;
    has_text: boolean;
    is_scanned: boolean;
    text_density: number;
    char_count: number;
    table_count: number;
    image_count: number;
  }>;
  continuation_groups: number[][];
}

export interface DocumentUnderstandingResponse {
  document_type: string;
  purpose: string;
  sections: string[];
  datasets: Array<{
    name: string;
    description: string;
    pages: number[];
    candidate_fields: string[];
    table_ids: string[];
    estimated_records?: number;
  }>;
  annexures: string[];
  continuation_tables_found: boolean;
  notes?: string;
}

export interface InferredField {
  field_name: string;
  source_label: string;
  data_type: 'string' | 'integer' | 'float' | 'boolean' | 'date';
  nullable: boolean;
  identifier: boolean;
  description?: string;
  relationship?: string;
  example_value?: string;
  preserve_leading_zero: boolean;
}

export interface SchemaInferenceResponse {
  dataset_name: string;
  description: string;
  fields: InferredField[];
  relationships_detected: string[];
  recommended_chunk_size: number;
}

export interface EvaluationReport {
  id: string;
  dataset_id: string;
  golden_dataset_name: string;
  evaluated_at: string;
  total_expected_records: number;
  total_actual_records: number;
  matched_records_count: number;
  missing_records_count: number;
  extra_records_count: number;
  field_mismatches_count: number;
  record_recall: number;
  record_precision: number;
  record_f1_score: number;
  field_accuracy: number;
  mismatches: Array<{
    row_index: number;
    field_name: string;
    expected_value: any;
    actual_value: any;
    identifier_value?: string;
  }>;
  missing_record_samples: Record<string, any>[];
  extra_record_samples: Record<string, any>[];
}

export interface ReconciliationResult {
  total_records_a: number;
  total_records_b: number;
  matched_records: number;
  agreement_rate: number;
  conflicts: ConflictRecord[];
  reconciled_records: Record<string, any>[];
}

export interface ResetDatabaseResponse {
  status: string;
  message: string;
  tables_recreated: number;
  files_removed: number;
}

