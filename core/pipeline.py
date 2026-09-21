from __future__ import annotations
import time
import platform
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from models.document import DocumentMetadata, DocumentStatus, DocumentType
from models.dataset import Dataset, DatasetMetadata
from models.field import FieldDefinition, DataType
from models.record import Record
from models.validation import ValidationSummary, IssueSeverity
from models.relationship import Relationship
from models.provenance import ProvenanceRecord, RecordStatus

from .inspector import DocumentInspector
from .classifier import DocumentClassifier
from .extractor_engine import ExtractorEngine
from .normalizer import Normalizer
from .schema_detector import SchemaDetector
from .relationship_detector import RelationshipDetector
from .validator import Validator
from .quality_scorer import QualityScorer
from .manifest import ExtractionManifest, ManifestDatasetSummary
from .project import Project


class PipelineStage(str, Enum):
    INGEST = "INGEST"
    INSPECT = "INSPECT"
    CLASSIFY = "CLASSIFY"
    EXTRACT = "EXTRACT"
    NORMALIZE = "NORMALIZE"
    VALIDATE = "VALIDATE"
    REVIEW = "REVIEW"
    EXPORT = "EXPORT"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    WARNING = "WARNING"
    FAILED = "FAILED"


class StageResult(BaseModel):
    stage: PipelineStage
    status: StageStatus = StageStatus.PENDING
    duration_seconds: float = 0.0
    record_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class PipelineRunResult(BaseModel):
    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    overall_status: StageStatus = StageStatus.COMPLETE
    stages: Dict[str, StageResult] = Field(default_factory=dict)
    datasets: List[Dataset] = Field(default_factory=list)
    validation_summary: Optional[ValidationSummary] = None
    manifest: Optional[ExtractionManifest] = None


class DataforgePipeline:
    """End-to-end multi-stage pipeline coordinator supporting selective and batch document transformation."""

    def __init__(self, project: Project, tesseract_cmd: str = ""):
        self.project = project
        from core.profile_loader import get_profile_loader
        self.profile_loader = get_profile_loader()
        self.inspector = DocumentInspector()
        self.classifier = DocumentClassifier(profile_loader=self.profile_loader)
        self.extractor_engine = ExtractorEngine(tesseract_cmd=tesseract_cmd)
        self.validator = Validator()

    def run_pipeline(
        self,
        document_ids: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[PipelineStage, float, str], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ) -> PipelineRunResult:
        run_id = self.project.increment_run()
        start_time = datetime.now(timezone.utc)
        stages_res: Dict[str, StageResult] = {}
        all_warnings: List[str] = []
        all_errors: List[str] = []

        def log(level: str, msg: str):
            if log_callback:
                log_callback(level, msg)
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{ts}] [{level}] {msg}")

        def notify(stage: PipelineStage, pct: float, msg: str):
            if progress_callback:
                progress_callback(stage, pct, msg)
            log("INFO", f"Stage {stage.value}: {msg}")

        # Filter documents based on selection
        if document_ids is not None:
            doc_id_set = set(str(did) for did in document_ids)
            docs_to_process = [d for d in self.project.documents.values() if str(d.id) in doc_id_set]
        else:
            docs_to_process = list(self.project.documents.values())

        if not docs_to_process:
            log("WARNING", "No documents queued for pipeline run.")
            return PipelineRunResult(
                run_id=run_id,
                overall_status=StageStatus.WARNING,
                stages={},
                datasets=[],
            )

        # -------------------------------------------------------------
        # 1. INSPECTION STAGE
        # -------------------------------------------------------------
        t0 = time.time()
        notify(PipelineStage.INSPECT, 0.10, f"Inspecting {len(docs_to_process)} document(s)...")
        stage_inspect = StageResult(stage=PipelineStage.INSPECT, status=StageStatus.RUNNING)

        for doc in docs_to_process:
            try:
                doc.inspection = self.inspector.inspect(doc.file_path)
                doc.status = DocumentStatus.INSPECTED
                log("INFO", f"Inspected {doc.filename}: {doc.inspection.page_count} pages, {doc.inspection.total_text_length} chars.")
            except Exception as e:
                stage_inspect.errors.append(f"Failed inspecting {doc.filename}: {e}")
                log("ERROR", f"Failed inspecting {doc.filename}: {e}")

        stage_inspect.duration_seconds = round(time.time() - t0, 2)
        stage_inspect.status = StageStatus.COMPLETE if not stage_inspect.errors else StageStatus.WARNING
        stages_res[PipelineStage.INSPECT.value] = stage_inspect

        # -------------------------------------------------------------
        # 2. CLASSIFICATION STAGE
        # -------------------------------------------------------------
        t0 = time.time()
        notify(PipelineStage.CLASSIFY, 0.25, "Classifying document structures...")
        stage_classify = StageResult(stage=PipelineStage.CLASSIFY, status=StageStatus.RUNNING)

        for doc in docs_to_process:
            try:
                doc.classification = self.classifier.classify(doc)
                doc.status = DocumentStatus.CLASSIFIED
                log("INFO", f"Classified {doc.filename} as {doc.classification.document_type.value} (conf: {doc.classification.confidence*100:.0f}%, extractor: {doc.classification.recommended_extractor})")
            except Exception as e:
                stage_classify.errors.append(f"Classification failed for {doc.filename}: {e}")
                log("ERROR", f"Classification failed for {doc.filename}: {e}")

        stage_classify.duration_seconds = round(time.time() - t0, 2)
        stage_classify.status = StageStatus.COMPLETE if not stage_classify.errors else StageStatus.WARNING
        stages_res[PipelineStage.CLASSIFY.value] = stage_classify

        # -------------------------------------------------------------
        # 3. EXTRACTION STAGE
        # -------------------------------------------------------------
        t0 = time.time()
        notify(PipelineStage.EXTRACT, 0.45, "Running extraction strategies...")
        stage_extract = StageResult(stage=PipelineStage.EXTRACT, status=StageStatus.RUNNING)
        extracted_tables_by_doc = {}
        total_raw_rows = 0

        for doc in docs_to_process:
            strategy = doc.effective_extractor or "pdf_tables"
            log("INFO", f"Extracting {doc.filename} using strategy '{strategy}'...")
            try:
                ext_result, winning_method = self.extractor_engine.extract(doc.file_path, strategy=strategy)
                extracted_tables_by_doc[doc.id] = (ext_result, winning_method)
                doc.manual_extractor_override = winning_method
                total_raw_rows += ext_result.total_rows
                log("INFO", f"Extracted {ext_result.total_rows} rows from {doc.filename} using '{winning_method}' (Quality: {ext_result.quality_score*100:.0f}%)")
                
                # Save raw extraction to disk for provenance audit
                self.project.workspace.save_raw_extraction(
                    doc.id,
                    {"filename": doc.filename, "method": winning_method, "tables": [t.model_dump() for t in ext_result.tables]}
                )
            except Exception as e:
                stage_extract.errors.append(f"Extraction failed for {doc.filename}: {e}")
                log("ERROR", f"Extraction error on {doc.filename}: {e}")

        stage_extract.record_count = total_raw_rows
        stage_extract.duration_seconds = round(time.time() - t0, 2)
        stage_extract.status = StageStatus.COMPLETE if total_raw_rows > 0 else StageStatus.FAILED
        stages_res[PipelineStage.EXTRACT.value] = stage_extract

        # -------------------------------------------------------------
        # 4. NORMALIZATION & RELATIONSHIP STAGE
        # -------------------------------------------------------------
        t0 = time.time()
        notify(PipelineStage.NORMALIZE, 0.65, "Normalizing values, schema & relationships...")
        stage_norm = StageResult(stage=PipelineStage.NORMALIZE, status=StageStatus.RUNNING)
        generated_datasets: List[Dataset] = []

        for doc in docs_to_process:
            if doc.id not in extracted_tables_by_doc:
                continue
            ext_result, method = extracted_tables_by_doc[doc.id]
            if not ext_result.tables:
                continue

            for t_idx, raw_table in enumerate(ext_result.tables):
                if not raw_table.rows:
                    continue

                # Lookup profile for this document
                profile = None
                if doc.classification:
                    profile = self.profile_loader.get_profile_by_document_type(doc.classification.document_type)
                    if not profile and doc.classification.recommended_extractor:
                        for p in self.profile_loader.get_all_profiles():
                            if p.recommended_extractor == doc.classification.recommended_extractor:
                                profile = p
                                break

                # Build Records with dual values and provenance
                raw_headers = raw_table.headers or [f"Col_{i+1}" for i in range(raw_table.column_count)]
                canonical_fields = SchemaDetector.detect_schema(raw_headers, [], profile=profile)

                table_records: List[Record] = []
                for r_idx, row in enumerate(raw_table.rows):
                    prov = ProvenanceRecord(
                        source_document=doc.filename,
                        source_document_id=doc.id,
                        source_page=raw_table.page_number,
                        source_row_idx=r_idx,
                        extraction_method=method,
                        confidence=raw_table.confidence,
                        status=RecordStatus.SOURCE_EXTRACTED,
                    )
                    record = Record(provenance=prov)
                    for c_idx, field_def in enumerate(canonical_fields):
                        cell_raw = row[c_idx] if c_idx < len(row) else ""
                        norm_val, is_mod = Normalizer.normalize_value(cell_raw, field_name=field_def.name)
                        record.set_value(field_def.name, cell_raw, norm_val, confidence=raw_table.confidence)
                    
                    record = Normalizer.normalize_record(record)
                    table_records.append(record)

                # Deduplicate records
                pk_fields = [f.name for f in canonical_fields if f.is_primary_key]
                if profile and profile.datasets and profile.datasets[0].primary_key:
                    pk_fields = [k for k in profile.datasets[0].primary_key if any(f.name == k for f in canonical_fields)] or pk_fields
                unique_records, dup_count = Normalizer.deduplicate_records(table_records, key_fields=pk_fields if pk_fields else None)
                if dup_count > 0:
                    log("INFO", f"Deduplicated {dup_count} duplicate rows in {doc.filename}.")

                # Base dataset name
                if profile and profile.datasets:
                    base_name = profile.datasets[0].id
                elif doc.classification and doc.classification.recommended_extractor == "qualifications":
                    base_name = "qualifications"
                elif doc.classification and doc.classification.recommended_extractor == "codebook":
                    base_name = "qlfs_codebook"
                elif doc.classification and doc.classification.recommended_extractor == "occupations":
                    base_name = "occupations_high_demand"
                else:
                    base_name = f"{doc.filename.lower().replace('.pdf', '')}_table"

                ds = Dataset(
                    metadata=DatasetMetadata(
                        name=base_name,
                        display_name=base_name.replace("_", " ").title(),
                        description=f"Extracted dataset from {doc.filename}",
                        source_documents=[doc.filename],
                    ),
                    columns=canonical_fields,
                    records=unique_records,
                    primary_key=pk_fields,
                )

                # Check for 1:N relationship decomposition
                list_col = RelationshipDetector.detect_list_column(ds)
                if list_col and pk_fields:
                    log("INFO", f"Detected 1:N relationship on column '{list_col.name}' for {ds.metadata.name}")
                    if profile and len(profile.datasets) > 1:
                        child_ds_name = profile.datasets[1].id
                    else:
                        child_ds_name = f"{ds.metadata.name}_colleges" if "college" in list_col.name else f"{ds.metadata.name}_items"
                    item_col_name = "college_name" if "college" in list_col.name else "item_name"

                    parent_clean, child_ds, rel = RelationshipDetector.decompose_one_to_many(
                        parent_dataset=ds,
                        list_column_name=list_col.name,
                        child_dataset_name=child_ds_name,
                        child_item_column_name=item_col_name,
                        parent_pk_column=pk_fields[0]
                    )
                    generated_datasets.append(parent_clean)
                    generated_datasets.append(child_ds)
                    self.project.relationships.append(rel)
                else:
                    generated_datasets.append(ds)

        stage_norm.record_count = sum(d.record_count for d in generated_datasets)
        stage_norm.duration_seconds = round(time.time() - t0, 2)
        stage_norm.status = StageStatus.COMPLETE
        stages_res[PipelineStage.NORMALIZE.value] = stage_norm

        # -------------------------------------------------------------
        # 5. VALIDATION & QUALITY SCORING STAGE
        # -------------------------------------------------------------
        t0 = time.time()
        notify(PipelineStage.VALIDATE, 0.85, "Executing rule-based validation and scoring quality...")
        stage_val = StageResult(stage=PipelineStage.VALIDATE, status=StageStatus.RUNNING)

        all_issues = []
        for ds in generated_datasets:
            summary = self.validator.validate_dataset(ds)
            all_issues.extend(summary.issues)
            # Calculate quality score
            ds.metadata.quality = QualityScorer.calculate_quality(
                ds,
                extraction_score=0.95,
                validation_summary=summary
            )
            log("INFO", f"Dataset '{ds.metadata.name}' Quality Score: {ds.metadata.quality.overall_score}% (Issues: {summary.critical_count} critical, {summary.warning_count} warnings)")

        combined_summary = ValidationSummary(
            critical_count=sum(1 for i in all_issues if i.severity == IssueSeverity.CRITICAL),
            warning_count=sum(1 for i in all_issues if i.severity == IssueSeverity.WARNING),
            info_count=sum(1 for i in all_issues if i.severity == IssueSeverity.INFO),
            total_issues=len(all_issues),
            records_with_issues=len(set(i.record_id for i in all_issues)),
            auto_fixable_count=sum(1 for i in all_issues if i.is_auto_fixable),
            issues=all_issues,
        )

        stage_val.record_count = len(all_issues)
        stage_val.duration_seconds = round(time.time() - t0, 2)
        stage_val.status = StageStatus.COMPLETE if combined_summary.critical_count == 0 else StageStatus.WARNING
        stages_res[PipelineStage.VALIDATE.value] = stage_val

        # Update datasets in project
        if document_ids is not None:
            # Selective execution: merge generated datasets with existing ones
            for ds in generated_datasets:
                self.project.datasets[ds.metadata.name] = ds
            self.project.store.save_datasets(list(self.project.datasets.values()))
            self.project.save()
        else:
            self.project.set_datasets(generated_datasets)

        self.project.validation_summary = combined_summary

        # -------------------------------------------------------------
        # 6. MANIFEST GENERATION
        # -------------------------------------------------------------
        notify(PipelineStage.EXPORT, 0.98, "Generating audit manifest...")
        manifest = ExtractionManifest(
            project_name=self.project.metadata.name,
            run_id=run_id,
            source_documents=[d.filename for d in docs_to_process],
            total_pages_inspected=sum(d.inspection.page_count for d in docs_to_process if d.inspection),
            total_records_extracted=sum(d.record_count for d in generated_datasets),
            records_valid=sum(d.record_count for d in generated_datasets) - combined_summary.records_with_issues,
            records_with_warnings=combined_summary.warning_count,
            records_critical=combined_summary.critical_count,
            extraction_methods=list(set(m for _, m in extracted_tables_by_doc.values())),
            datasets=[
                ManifestDatasetSummary(
                    name=d.metadata.name,
                    record_count=d.record_count,
                    column_count=len(d.columns),
                    columns=d.column_names,
                    quality_score=d.metadata.quality.overall_score if d.metadata.quality else 0.0,
                ) for d in generated_datasets
            ],
            system_environment={
                "platform": platform.system(),
                "platform_release": platform.release(),
                "engine": "Darkroom DataForge v1.0.0"
            }
        )
        self.project.workspace.save_manifest(manifest.model_dump(mode="json"))

        notify(PipelineStage.REVIEW, 1.0, f"Pipeline complete: {manifest.total_records_extracted} records across {len(generated_datasets)} datasets.")

        return PipelineRunResult(
            run_id=run_id,
            started_at=start_time,
            completed_at=datetime.now(timezone.utc),
            overall_status=StageStatus.COMPLETE if combined_summary.critical_count == 0 else StageStatus.WARNING,
            stages=stages_res,
            datasets=generated_datasets,
            validation_summary=combined_summary,
            manifest=manifest,
        )
