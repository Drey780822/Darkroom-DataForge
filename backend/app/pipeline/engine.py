import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.validation_issue import ValidationIssue
from backend.app.models.extraction_job import ExtractionJob
from backend.app.models.activity import ActivityLog
from backend.app.models.college import College
from backend.app.models.qualification import (
    Qualification,
    QualificationCollege,
    DsppCentreOfSpecialisation,
)
from backend.app.models.metadata import (
    DataDictionaryEntry,
    ProvenanceRecord,
    ReviewRequired,
)
from backend.app.extractors import (
    QualificationsExtractor,
    OccupationsExtractor,
    CodebookExtractor,
    PdfTablesExtractor,
    BaseExtractor,
)
from backend.app.pipeline.normalizer import Normalizer
from backend.app.pipeline.schema_detector import SchemaDetector
from backend.app.pipeline.validator import (
    Validator,
    ALLOWED_NSFAS_ALLOWANCES,
    ALLOWED_CONFIDENCE_LEVELS,
    ALLOWED_NQF_SUB_FRAMEWORKS,
)
from backend.app.llm.router import LLMRouter, ExtractionMode, EscalationLevel
from backend.app.llm.schemas import (
    DocumentIntelligenceMap,
    DocumentUnderstandingResponse,
    SchemaInferenceResponse,
    ChunkExtractionResponse,
    LLMValidationResponse,
)
from backend.app.prompts import (
    EXTRACTION_PROMPT_VERSION,
    document_analysis,
    schema_analysis,
    extraction as extraction_prompts,
    validation as validation_prompts,
)
from backend.app.services.document_inspector import DocumentInspectorService
from backend.app.services.chunk_manager import ChunkManagerService
from backend.app.services.reconciliation_engine import ReconciliationEngineService
from backend.app.services.manifest_generator import ManifestGeneratorService

logger = logging.getLogger("dataforge.pipeline")

GENERIC_COLLEGE_STOPWORDS = {
    "college",
    "colleges",
    "tvet",
    "tvet college",
    "tvet colleges",
    "participating",
    "participating colleges",
    "participating tvet colleges",
    "none",
    "nil",
    "n/a",
    "na",
    "no",
    "-",
    "--",
}

def parse_and_clean_colleges(raw_colleges: Any) -> List[str]:
    """Robustly extracts individual college names from raw table text,
    handling wrapped lines, multi-line cells, semicolons, and bullets.
    """
    if not raw_colleges:
        return []

    raw_items = []
    if isinstance(raw_colleges, list):
        raw_items = [str(x) for x in raw_colleges]
    elif isinstance(raw_colleges, str):
        text = raw_colleges.strip()
        if ";" in text:
            raw_items = text.split(";")
        elif "•" in text or "·" in text:
            raw_items = re.split(r"[•·]+", text)
        elif "\n" in text:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            stitched = []
            for line in lines:
                clow = line.lower()
                if stitched and (
                    clow in ["college", "colleges", "tvet", "tvet college", "tvet colleges", "campus"]
                    or clow.startswith("college")
                    or clow.startswith("campus")
                    or stitched[-1].endswith(",")
                    or stitched[-1].endswith("-")
                ):
                    stitched[-1] = f"{stitched[-1]} {line}".strip()
                else:
                    stitched.append(line)
            raw_items = stitched
        else:
            raw_items = [text]
    else:
        raw_items = [str(raw_colleges)]

    clean_colleges = []
    for item in raw_items:
        c_clean = re.sub(r"\s+", " ", str(item)).strip(" \t\r\n;,•·-")
        if not c_clean or len(c_clean) < 3:
            continue
        if c_clean.lower() in GENERIC_COLLEGE_STOPWORDS:
            continue
        c_clean = re.sub(r"^\d+[\.\)]\s*", "", c_clean).strip()
        if c_clean and c_clean.lower() not in GENERIC_COLLEGE_STOPWORDS:
            clean_colleges.append(c_clean)

    # Deduplicate while preserving order
    seen = set()
    result = []
    for c in clean_colleges:
        if c.lower() not in seen:
            seen.add(c.lower())
            result.append(c)

    return result

class PipelineEngine:
    """Orchestrates document intelligence, layout reconstruction, LLM structured extraction, dual validation, and dataset generation."""

    @classmethod
    def select_extractor(cls, doc_type: str, pipeline_type: str) -> BaseExtractor:
        target = pipeline_type if pipeline_type != "auto" else doc_type
        target = (target or "").lower()

        if "qual" in target or "tvet" in target:
            return QualificationsExtractor()
        elif "occup" in target or "oihd" in target or "ofo" in target:
            return OccupationsExtractor()
        elif "codebook" in target or "qlfs" in target or "survey" in target:
            return CodebookExtractor()
        else:
            return PdfTablesExtractor()

    @classmethod
    def run_pipeline(
        cls,
        db: Session,
        job_id: str,
        document_ids: List[str],
        pipeline_type: str = "auto",
        parameters: Optional[Dict[str, Any]] = None,
        target_dataset_name: Optional[str] = None,
    ) -> Optional[Dataset]:
        job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
        if not job:
            logger.error(f"Extraction job {job_id} not found.")
            return None

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress = 5
        job.step_status = "inspecting"
        db.commit()

        start_time = time.time()
        parameters = parameters or {}
        pages = parameters.get("pages")  # e.g. [1, 2, 3]
        extraction_mode = parameters.get("extraction_mode") or job.extraction_mode or "high_accuracy"
        provider_name = parameters.get("provider") or job.provider or "deepseek"
        model_name = parameters.get("model") or job.primary_model or "deepseek-reasoner"
        secondary_model = parameters.get("secondary_model") or job.secondary_model
        fallback_model = parameters.get("fallback_model")
        schema_override = parameters.get("schema_override")
        use_vision = parameters.get("use_vision", "auto")

        job.provider = provider_name
        job.primary_model = model_name
        job.secondary_model = secondary_model
        job.prompt_version = EXTRACTION_PROMPT_VERSION
        db.commit()

        try:
            documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
            if not documents:
                raise ValueError("No valid documents found for extraction.")

            primary_doc = documents[0]
            file_path = primary_doc.file_path
            doc_hash = DocumentInspectorService.compute_file_hash(file_path)

            # -------------------------------------------------------------
            # STAGE 1: Deep Document Inspection & Intelligence Map
            # -------------------------------------------------------------
            logger.info(f"Inspecting document layout and topology for {primary_doc.filename}...")
            doc_map = DocumentInspectorService.inspect_document(primary_doc.id, file_path, primary_doc.filename)
            job.progress = 15
            job.step_status = "understanding"
            db.commit()

            # Determine whether to use LLM extraction or Deterministic
            use_llm = extraction_mode in [
                ExtractionMode.BALANCED,
                ExtractionMode.HIGH_ACCURACY,
                ExtractionMode.MAXIMUM_ACCURACY,
            ] or parameters.get("use_llm", False)

            extracted_records_list: List[Dict[str, Any]] = []
            extracted_records_secondary: List[Dict[str, Any]] = []
            schema_columns: List[Dict[str, Any]] = []
            conflicts_list: List[Any] = []
            total_tokens = 0
            total_cost = 0.0

            # -------------------------------------------------------------
            # STAGE 2: LLM Document Understanding & Schema Inference
            # -------------------------------------------------------------
            if use_llm:
                logger.info(f"Executing LLM Document Understanding pass using {provider_name}:{model_name}...")
                try:
                    # Pass 1: Document Understanding
                    page_samples = [
                        {"page_number": p.page_number, "text_preview": DocumentInspectorService.get_page_text(file_path, p.page_number)}
                        for p in doc_map.pages[:4]
                    ]
                    und_user_prompt = document_analysis.build_document_analysis_user_prompt(
                        filename=primary_doc.original_name,
                        page_count=doc_map.page_count,
                        detected_sections=[s.model_dump() for s in doc_map.sections],
                        detected_tables=[t.model_dump() for t in doc_map.tables],
                        page_samples=page_samples,
                    )
                    und_resp, _ = LLMRouter.execute_structured_with_fallback(
                        schema=DocumentUnderstandingResponse,
                        system_prompt=document_analysis.DOCUMENT_ANALYSIS_SYSTEM_PROMPT,
                        user_prompt=und_user_prompt,
                        primary_provider=provider_name,
                        primary_model=model_name,
                        fallback_provider=provider_name,
                        fallback_model=fallback_model,
                    )
                    total_tokens += und_resp.total_tokens
                    total_cost += und_resp.estimated_cost_usd

                    # Pass 2: Schema Inference (or use user override)
                    job.progress = 25
                    job.step_status = "inferring_schema"
                    db.commit()

                    if schema_override:
                        schema_columns = schema_override
                    else:
                        cand_fields = []
                        if und_resp.parsed and und_resp.parsed.datasets:
                            cand_fields = und_resp.parsed.datasets[0].candidate_fields
                        sample_txt = page_samples[0]["text_preview"] if page_samples else ""
                        sample_rows = doc_map.tables[0].headers if doc_map.tables else []

                        schema_user_prompt = schema_analysis.build_schema_analysis_user_prompt(
                            dataset_name=target_dataset_name or primary_doc.original_name,
                            candidate_fields=cand_fields,
                            sample_pages_text=sample_txt,
                            sample_table_rows=[sample_rows],
                        )
                        sch_resp, _ = LLMRouter.execute_structured_with_fallback(
                            schema=SchemaInferenceResponse,
                            system_prompt=schema_analysis.SCHEMA_ANALYSIS_SYSTEM_PROMPT,
                            user_prompt=schema_user_prompt,
                            primary_provider=provider_name,
                            primary_model=model_name,
                            fallback_provider=provider_name,
                            fallback_model=fallback_model,
                        )
                        total_tokens += sch_resp.total_tokens
                        total_cost += sch_resp.estimated_cost_usd

                        if sch_resp.parsed and sch_resp.parsed.fields:
                            schema_columns = [
                                {
                                    "name": f.field_name,
                                    "original_name": f.source_label,
                                    "type": f.data_type,
                                    "required": not f.nullable,
                                    "identifier": f.identifier,
                                    "description": f.description or f.source_label,
                                }
                                for f in sch_resp.parsed.fields
                            ]

                    # -------------------------------------------------------------
                    # STAGE 3: Chunk-Aware Structured Extraction
                    # -------------------------------------------------------------
                    job.progress = 35
                    job.step_status = "extracting"
                    db.commit()

                    chunks = ChunkManagerService.create_chunks(
                        file_path=file_path,
                        doc_map=doc_map,
                        pages_to_process=pages,
                        chunk_size=4,
                    )

                    target_field_names = [c["name"] for c in schema_columns] if schema_columns else ["item", "description", "value"]

                    for c_idx, chunk in enumerate(chunks):
                        cache_key = ChunkManagerService.get_cache_key(
                            doc_hash=doc_hash,
                            chunk_start=chunk.page_start,
                            chunk_end=chunk.page_end,
                            model=model_name,
                            prompt_version=EXTRACTION_PROMPT_VERSION,
                        )
                        cached_chunk = ChunkManagerService.get_cached_response(cache_key)

                        if cached_chunk:
                            logger.info(f"Using cached extraction for chunk {c_idx + 1}/{len(chunks)}...")
                            chunk_res = cached_chunk
                        else:
                            images = None
                            if use_vision == "always" or (use_vision == "auto" and doc_map.is_scanned):
                                images = [
                                    DocumentInspectorService.render_page_image(file_path, chunk.page_start)
                                ]

                            chunk_prompt = extraction_prompts.build_chunk_extraction_user_prompt(
                                dataset_name=target_dataset_name or primary_doc.original_name,
                                target_fields=target_field_names,
                                chunk_page_start=chunk.page_start,
                                chunk_page_end=chunk.page_end,
                                chunk_text=chunk.text,
                                rules=["Reconstruct broken rows.", "Preserve leading zeroes."],
                                previous_overlap_text=chunk.previous_overlap_text,
                                is_continuation=chunk.is_continuation,
                            )
                            c_resp, _ = LLMRouter.execute_structured_with_fallback(
                                schema=ChunkExtractionResponse,
                                system_prompt=extraction_prompts.EXTRACTION_SYSTEM_PROMPT,
                                user_prompt=chunk_prompt,
                                primary_provider=provider_name,
                                primary_model=model_name,
                                fallback_provider=provider_name,
                                fallback_model=fallback_model,
                                images=images,
                            )
                            chunk_res = c_resp.parsed
                            total_tokens += c_resp.total_tokens
                            total_cost += c_resp.estimated_cost_usd
                            if chunk_res:
                                ChunkManagerService.set_cached_response(cache_key, chunk_res)

                        if chunk_res and chunk_res.records:
                            for rec_item in chunk_res.records:
                                extracted_records_list.append({
                                    "data": rec_item.data,
                                    "raw_data": rec_item.raw_data or rec_item.data,
                                    "source_page": rec_item.source_page,
                                    "confidence": rec_item.confidence,
                                    "issues": rec_item.issues,
                                    "field_provenance": rec_item.field_provenance,
                                })

                        # Update progress incrementally
                        pct = 35 + int(35 * ((c_idx + 1) / max(1, len(chunks))))
                        job.progress = pct
                        db.commit()

                    # Optional Secondary Model extraction for MAXIMUM_ACCURACY
                    if extraction_mode == ExtractionMode.MAXIMUM_ACCURACY and secondary_model:
                        logger.info(f"Running secondary model verification pass with {secondary_model}...")
                        # Run extraction on first 2 chunks for verification
                        for chunk in chunks[:2]:
                            sec_prompt = extraction_prompts.build_chunk_extraction_user_prompt(
                                dataset_name=target_dataset_name or primary_doc.original_name,
                                target_fields=target_field_names,
                                chunk_page_start=chunk.page_start,
                                chunk_page_end=chunk.page_end,
                                chunk_text=chunk.text,
                            )
                            sec_resp, _ = LLMRouter.execute_structured_with_fallback(
                                schema=ChunkExtractionResponse,
                                system_prompt=extraction_prompts.EXTRACTION_SYSTEM_PROMPT,
                                user_prompt=sec_prompt,
                                primary_provider=provider_name,
                                primary_model=secondary_model,
                            )
                            total_tokens += sec_resp.total_tokens
                            total_cost += sec_resp.estimated_cost_usd
                            if sec_resp.parsed:
                                for rec_item in sec_resp.parsed.records:
                                    extracted_records_secondary.append(rec_item.data)

                        # Reconcile Model A vs Model B
                        recon_result = ReconciliationEngineService.reconcile(
                            records_a=[r["data"] for r in extracted_records_list],
                            records_b=extracted_records_secondary,
                            model_a_name=model_name,
                            model_b_name=secondary_model,
                        )
                        conflicts_list = [c.model_dump() for c in recon_result.conflicts]
                        job.conflicts = conflicts_list
                        logger.info(f"Reconciliation agreement rate: {recon_result.agreement_rate}% ({len(conflicts_list)} conflicts)")

                except Exception as llm_err:
                    logger.warning(f"LLM extraction encountered an error: {llm_err}. Falling back to deterministic table extraction...")
                    use_llm = False

            # -------------------------------------------------------------
            # STAGE 4: Fallback / Deterministic Extraction
            # -------------------------------------------------------------
            if not use_llm or not extracted_records_list:
                logger.info("Executing deterministic extraction pipeline...")
                extractor = cls.select_extractor(primary_doc.doc_type, pipeline_type)
                res = extractor.extract(file_path, pages=pages)

                if not res.tables and not isinstance(extractor, PdfTablesExtractor):
                    logger.info("Specialized extractor found 0 tables. Falling back to PdfTablesExtractor.")
                    fallback_extractor = PdfTablesExtractor()
                    res = fallback_extractor.extract(file_path, pages=pages)

                if not res.tables:
                    raise ValueError("No tabular data or structured records could be detected in the document.")

                first_tab = res.tables[0]
                if not schema_columns:
                    schema_columns = SchemaDetector.detect_columns(first_tab.headers, first_tab.rows[:20])

                col_names = [c["name"] for c in schema_columns]

                for tab in res.tables:
                    for row_cells in tab.rows:
                        row_dict = {}
                        for c_idx, col_name in enumerate(col_names):
                            row_dict[col_name] = row_cells[c_idx] if c_idx < len(row_cells) else ""
                        extracted_records_list.append({
                            "data": row_dict,
                            "raw_data": row_dict,
                            "source_page": tab.page_number,
                            "confidence": tab.confidence,
                            "issues": [],
                        })

            # -------------------------------------------------------------
            # STAGE 5: Normalization, Dual Validation & Dataset Persistence
            # -------------------------------------------------------------
            job.progress = 75
            job.step_status = "validating"
            db.commit()

            ds_name = target_dataset_name
            if not ds_name:
                base_name = primary_doc.original_name.rsplit(".", 1)[0]
                ds_name = f"{base_name} - Structured Dataset"

            dataset = Dataset(
                project_id=job.project_id,
                document_id=primary_doc.id,
                name=ds_name,
                description=f"Generated via {'Intelligent LLM' if use_llm else 'Deterministic'} pipeline ({job.primary_model or 'Native'}).",
                schema_name=primary_doc.doc_type,
                schema_columns=schema_columns,
                document_map=doc_map.model_dump(),
                status="normalized",
            )
            db.add(dataset)
            db.flush()

            job.dataset_id = dataset.id
            db.commit()

            # Route reconciliation model disagreements to review_required
            if conflicts_list:
                for conflict in conflicts_list:
                    c_dict = conflict if isinstance(conflict, dict) else (conflict.model_dump() if hasattr(conflict, "model_dump") else {})
                    val_a = c_dict.get("model_a_value", c_dict.get("field_value_a", ""))
                    val_b = c_dict.get("model_b_value", c_dict.get("field_value_b", ""))
                    f_name = c_dict.get("field_name", "field")
                    p_num = str(c_dict.get("page_number", c_dict.get("source_page", 1)))
                    agr = c_dict.get("agreement_score")
                    Validator.route_to_review_required(
                        db=db,
                        original_value=str(val_a or val_b or ""),
                        issue=f"model_disagreement_{f_name}",
                        source_page=p_num,
                        reason=f"Model disagreement between {job.primary_model or 'Model A'} ('{val_a}') and {job.secondary_model or 'Model B'} ('{val_b}')",
                        job_id=job.id,
                        document_id=primary_doc.id,
                        dataset_id=dataset.id,
                        agreement_score=agr,
                    )

            error_records_count = 0
            warning_records_count = 0
            records_entities = []

            # In-memory deduplication trackers to prevent session duplicate flush violations
            seen_qualifications = set()
            seen_qualification_colleges = set()
            seen_dspp_centres = set()

            for r_idx, r_item in enumerate(extracted_records_list):
                row_num = r_idx + 1
                raw_dict = r_item.get("data", {})
                norm_data, raw_data = Normalizer.normalize_record(raw_dict)

                # Deterministic validation checks
                issues = Validator.validate_record(norm_data, schema_columns, row_num)
                rec_status = "valid"
                if any(i["severity"] == "error" for i in issues):
                    rec_status = "error"
                    error_records_count += 1
                elif any(i["severity"] == "warning" for i in issues) or r_item.get("issues"):
                    rec_status = "warning"
                    warning_records_count += 1

                prov = {
                    "document_id": primary_doc.id,
                    "document_name": primary_doc.original_name,
                    "page_number": r_item.get("source_page", 1),
                    "method": "llm_structured_extraction" if use_llm else "deterministic_table",
                    "model": job.primary_model or "deterministic",
                    "prompt_version": EXTRACTION_PROMPT_VERSION if use_llm else None,
                }

                rec = Record(
                    dataset_id=dataset.id,
                    row_index=row_num,
                    data=norm_data,
                    raw_data=raw_data,
                    confidence_score=r_item.get("confidence", 1.0),
                    provenance=prov,
                    status=rec_status,
                )
                db.add(rec)
                db.flush()
                records_entities.append(rec)

                for issue in issues:
                    db.add(
                        ValidationIssue(
                            dataset_id=dataset.id,
                            record_id=rec.id,
                            row_index=row_num,
                            column_name=issue["column_name"],
                            rule_name=issue["rule_name"],
                            severity=issue["severity"],
                            message=issue["message"],
                            raw_value=issue.get("raw_value"),
                        )
                    )

                # Relational Schema Persistence: qualifications, colleges, qualification_colleges, dspp_centres
                saqa_candidate = str(
                    norm_data.get("saqa_id")
                    or norm_data.get("qual_id")
                    or raw_dict.get("saqa_id")
                    or raw_dict.get("qual_id")
                    or ""
                ).strip()

                is_qualification_record = (
                    bool(re.search(r"\d{4,}", saqa_candidate))
                    or "qualification" in str(primary_doc.doc_type).lower()
                    or "saqa_id" in norm_data
                    or "qualification_name" in norm_data
                    or "qualification" in norm_data
                )

                if is_qualification_record:
                    q_name = str(
                        norm_data.get("qualification_name")
                        or norm_data.get("qualification")
                        or norm_data.get("qualification_title")
                        or raw_dict.get("qualification")
                        or raw_dict.get("qualification_name")
                        or "Unknown Qualification"
                    ).strip()
                    q_raw = str(
                        raw_dict.get("qualification")
                        or raw_dict.get("qualification_name")
                        or raw_dict.get("qualification_title")
                        or q_name
                    )
                    q_num = str(
                        norm_data.get("qualification_number")
                        or norm_data.get("qual_no")
                        or norm_data.get("qualification_no")
                        or raw_dict.get("qual_no")
                        or saqa_candidate
                        or str(row_num)
                    ).strip()
                    nqf_lvl = str(norm_data.get("nqf_level") or raw_dict.get("nqf_level") or "").strip() or None

                    # Framework mapping & validation
                    raw_fw = str(norm_data.get("nqf_sub_framework") or norm_data.get("framework") or norm_data.get("sub_framework") or "OQSF").strip().upper()
                    if "OQSF" in raw_fw or "OCCUPATIONAL" in raw_fw:
                        clean_fw = "OQSF"
                    elif "HEQSF" in raw_fw or "HIGHER" in raw_fw:
                        clean_fw = "HEQSF"
                    elif "GFET" in raw_fw or "GENERAL" in raw_fw or "FURTHER" in raw_fw:
                        clean_fw = "GFETQSF"
                    else:
                        clean_fw = raw_fw

                    # NSFAS allowance normalization
                    raw_nsfas = str(norm_data.get("nsfas_allowance") or norm_data.get("nsfas_eligible") or norm_data.get("nsfas") or "").strip()
                    if raw_nsfas.upper() in ["YES", "ELIGIBLE", "FUNDED", "TRUE", "1", "Y"]:
                        clean_nsfas = "YES"
                    elif raw_nsfas.upper() in ["NO", "NOT ELIGIBLE", "UNFUNDED", "FALSE", "0", "N"]:
                        clean_nsfas = "NO"
                    else:
                        clean_nsfas = raw_nsfas.upper() if raw_nsfas else "NO"

                    # Confidence level normalization
                    conf_raw = r_item.get("confidence", 1.0)
                    if isinstance(conf_raw, (int, float)):
                        if conf_raw >= 0.85:
                            clean_conf = "high"
                        elif conf_raw >= 0.60:
                            clean_conf = "medium"
                        else:
                            clean_conf = "low"
                    else:
                        c_str = str(conf_raw).lower().strip()
                        clean_conf = c_str if c_str in ALLOWED_CONFIDENCE_LEVELS else "medium"

                    src_sec = str(r_item.get("source_section") or norm_data.get("source_section") or "Section 1: Occupational Qualifications")
                    src_page = str(r_item.get("source_page", 1))

                    qual_dict = {
                        "saqa_id": saqa_candidate,
                        "qualification_number": q_num,
                        "qualification_name": q_name,
                        "qualification_name_raw": q_raw,
                        "nqf_level": nqf_lvl,
                        "nqf_sub_framework": clean_fw,
                        "nsfas_allowance": clean_nsfas,
                        "source_section": src_sec,
                        "source_page": src_page,
                        "confidence": clean_conf,
                        "extraction_note": r_item.get("extraction_note"),
                    }

                    is_valid_qual, qual_violations = Validator.validate_qualification_constraints(qual_dict, row_index=row_num)
                    if not is_valid_qual:
                        for v in qual_violations:
                            Validator.route_to_review_required(
                                db=db,
                                original_value=v["raw_value"],
                                issue=v["rule_name"],
                                source_page=src_page,
                                reason=v["message"],
                                job_id=job.id,
                                document_id=primary_doc.id,
                                dataset_id=dataset.id,
                                agreement_score=None,
                            )
                    else:
                        # Insert or update in qualifications parent table
                        if saqa_candidate not in seen_qualifications:
                            existing_qual = db.query(Qualification).filter(Qualification.saqa_id == saqa_candidate).first()
                            if not existing_qual:
                                qual_obj = Qualification(
                                    saqa_id=saqa_candidate,
                                    qualification_number=q_num,
                                    qualification_name=q_name,
                                    qualification_name_raw=q_raw,
                                    nqf_level=nqf_lvl,
                                    nqf_sub_framework=clean_fw,
                                    nsfas_allowance=clean_nsfas,
                                    source_section=src_sec,
                                    source_page=src_page,
                                    confidence=clean_conf,
                                    extraction_note=r_item.get("extraction_note"),
                                    job_id=job.id,
                                    document_id=primary_doc.id,
                                )
                                db.add(qual_obj)
                                db.flush()
                            seen_qualifications.add(saqa_candidate)

                        # Normalize colleges & junction tables using robust parsing
                        raw_colleges = (
                            norm_data.get("colleges")
                            or norm_data.get("participating_colleges")
                            or raw_dict.get("participating_colleges")
                            or raw_dict.get("colleges")
                        )
                        college_list = parse_and_clean_colleges(raw_colleges)

                        is_dspp = (
                            "dspp" in src_sec.lower()
                            or "centre of specialisation" in src_sec.lower()
                            or "specialisation" in src_sec.lower()
                            or norm_data.get("programme_context")
                            or norm_data.get("specialisation_trade")
                        )
                        prog_context = str(
                            norm_data.get("programme_context")
                            or norm_data.get("specialisation_trade")
                            or q_name
                        )

                        for c_name in college_list:
                            if not c_name:
                                continue
                            college_entity = College.get_or_create(db, c_name)
                            if not college_entity:
                                continue

                            pair_key = (saqa_candidate, college_entity.college_id)

                            # 1. qualification_colleges
                            if pair_key not in seen_qualification_colleges:
                                qc_exists = db.query(QualificationCollege).filter(
                                    QualificationCollege.saqa_id == saqa_candidate,
                                    QualificationCollege.college_id == college_entity.college_id,
                                ).first()
                                if not qc_exists:
                                    qc_obj = QualificationCollege(
                                        saqa_id=saqa_candidate,
                                        qualification_number=q_num,
                                        college_id=college_entity.college_id,
                                        college_name=college_entity.college_name,
                                        source_section=src_sec,
                                        source_page=src_page,
                                        job_id=job.id,
                                        document_id=primary_doc.id,
                                    )
                                    db.add(qc_obj)
                                seen_qualification_colleges.add(pair_key)

                            # 2. dspp_centres_of_specialisation (if DSPP context)
                            if is_dspp and pair_key not in seen_dspp_centres:
                                dspp_exists = db.query(DsppCentreOfSpecialisation).filter(
                                    DsppCentreOfSpecialisation.saqa_id == saqa_candidate,
                                    DsppCentreOfSpecialisation.college_id == college_entity.college_id,
                                ).first()
                                if not dspp_exists:
                                    dspp_obj = DsppCentreOfSpecialisation(
                                        saqa_id=saqa_candidate,
                                        qualification_number=q_num,
                                        college_id=college_entity.college_id,
                                        college_name=college_entity.college_name,
                                        source_section=src_sec,
                                        source_page=src_page,
                                        programme_context=prog_context,
                                        job_id=job.id,
                                        document_id=primary_doc.id,
                                    )
                                    db.add(dspp_obj)
                                seen_dspp_centres.add(pair_key)

            # -------------------------------------------------------------
            # STAGE 6: Quality Metrics & Research Artifact Bundle
            # -------------------------------------------------------------
            total_records = len(extracted_records_list)
            valid_count = total_records - error_records_count - warning_records_count
            quality_score = Validator.calculate_quality_score(
                total_records, error_records_count, warning_records_count
            )

            dataset.record_count = total_records
            dataset.valid_record_count = valid_count
            dataset.warning_record_count = warning_records_count
            dataset.error_record_count = error_records_count
            dataset.quality_score = quality_score
            dataset.status = "validated"

            # Populate normalized data_dictionary table
            for col in schema_columns:
                col_name = col.get("name")
                if not col_name:
                    continue
                existing_entry = db.query(DataDictionaryEntry).filter(
                    DataDictionaryEntry.job_id == job.id,
                    DataDictionaryEntry.dataset_name == dataset.name,
                    DataDictionaryEntry.column_name == col_name,
                ).first()
                if not existing_entry:
                    is_null = "false" if col.get("required") else "true"
                    db.add(DataDictionaryEntry(
                        job_id=job.id,
                        document_id=primary_doc.id,
                        dataset_name=dataset.name,
                        column_name=col_name,
                        data_type=str(col.get("type", "string")),
                        description=str(col.get("description") or f"Extracted column {col_name}"),
                        source_field=str(col.get("original_name") or col.get("source_label") or col_name),
                        nullable=is_null,
                        example_value=str(col.get("example", "")) if col.get("example") is not None else None,
                    ))

            # Populate normalized provenance table
            existing_prov = db.query(ProvenanceRecord).filter(
                ProvenanceRecord.job_id == job.id,
                ProvenanceRecord.dataset_name == dataset.name,
            ).first()
            page_range_str = f"1-{getattr(doc_map, 'page_count', 1)}"
            if not existing_prov:
                db.add(ProvenanceRecord(
                    job_id=job.id,
                    document_id=primary_doc.id,
                    dataset_name=dataset.name,
                    source_document=primary_doc.original_name,
                    source_section=getattr(primary_doc, "doc_type", "general") or "general",
                    source_page=page_range_str,
                    extraction_method="llm_structured_extraction" if use_llm else "deterministic_table",
                    record_count=total_records,
                ))
            else:
                existing_prov.record_count = total_records

            # Generate Data Dictionary & Provenance bundle
            try:
                bundle_files = ManifestGeneratorService.generate_artifact_bundle(
                    dataset_name=dataset.name,
                    document_filename=primary_doc.original_name,
                    document_hash=doc_hash,
                    page_count=doc_map.page_count,
                    schema_columns=schema_columns,
                    records=[r.data for r in records_entities],
                    models_used=[m for m in [job.primary_model, job.secondary_model] if m],
                    prompt_version=EXTRACTION_PROMPT_VERSION,
                    profile_name=primary_doc.doc_type,
                    db=db,
                    job_id=job.id,
                )
                logger.info(f"Artifact bundle generated: {bundle_files}")
            except Exception as b_err:
                logger.warning(f"Bundle generation warning: {b_err}")

            duration_ms = int((time.time() - start_time) * 1000)
            job.status = "completed"
            job.progress = 100
            job.step_status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.tokens_used = total_tokens
            job.estimated_cost = total_cost
            job.metrics = {
                "records_extracted": total_records,
                "valid_records": valid_count,
                "errors_count": error_records_count,
                "warnings_count": warning_records_count,
                "quality_score": quality_score,
                "duration_ms": duration_ms,
                "tokens_used": total_tokens,
                "estimated_cost_usd": total_cost,
                "conflicts_count": len(conflicts_list),
            }

            for doc in documents:
                doc.status = "extracted"

            activity = ActivityLog(
                project_id=job.project_id,
                entity_type="dataset",
                entity_id=dataset.id,
                action="extracted",
                description=f"Generated intelligent dataset '{dataset.name}' with {total_records} records ({quality_score}% quality, {total_tokens} tokens).",
                user=f"Pipeline Engine ({job.primary_model or 'Native'})",
                details=job.metrics,
            )
            db.add(activity)

            db.commit()
            return dataset

        except Exception as e:
            logger.exception("Pipeline execution failed")
            db.rollback()
            job.status = "failed"
            job.step_status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return None
