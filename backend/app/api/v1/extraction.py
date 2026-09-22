import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, SessionLocal
from backend.app.models.document import Document
from backend.app.models.project import Project
from backend.app.models.extraction_job import ExtractionJob
from backend.app.models.activity import ActivityLog
from backend.app.schemas.extraction import (
    ExtractionJobCreate,
    ExtractionJobResponse,
    ResolveConflictRequest,
)
from backend.app.pipeline.engine import PipelineEngine
from backend.app.services.document_inspector import DocumentInspectorService
from backend.app.llm.schemas import (
    DocumentIntelligenceMap,
    DocumentUnderstandingResponse,
    SchemaInferenceResponse,
)
from backend.app.llm.router import LLMRouter
from backend.app.prompts import document_analysis, schema_analysis

router = APIRouter(prefix="/extraction", tags=["Extraction"])

def run_extraction_worker(job_id: str, document_ids: List[str], pipeline_type: str, parameters: dict, target_dataset_name: Optional[str]):
    db = SessionLocal()
    try:
        PipelineEngine.run_pipeline(
            db=db,
            job_id=job_id,
            document_ids=document_ids,
            pipeline_type=pipeline_type,
            parameters=parameters,
            target_dataset_name=target_dataset_name,
        )
    finally:
        db.close()

@router.get("/jobs", response_model=List[ExtractionJobResponse])
def list_jobs(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ExtractionJob)
    if project_id:
        query = query.filter(ExtractionJob.project_id == project_id)
    return query.order_by(ExtractionJob.created_at.desc()).all()

@router.post("/jobs", response_model=ExtractionJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_extraction_job(
    payload: ExtractionJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = db.query(Document).filter(Document.id.in_(payload.document_ids)).all()
    if not docs:
        raise HTTPException(status_code=400, detail="No valid documents selected")

    params = payload.parameters or {}
    params["extraction_mode"] = payload.extraction_mode
    params["provider"] = payload.provider
    params["model"] = payload.model
    params["secondary_model"] = payload.secondary_model

    job_id = str(uuid.uuid4())
    job = ExtractionJob(
        id=job_id,
        project_id=payload.project_id,
        document_id=docs[0].id,
        pipeline_type=payload.pipeline_type,
        extraction_mode=payload.extraction_mode or "high_accuracy",
        primary_model=payload.model,
        secondary_model=payload.secondary_model,
        provider=payload.provider,
        status="pending",
        step_status="pending",
        parameters=params,
        progress=0,
        metrics={},
        conflicts=[],
    )
    db.add(job)

    activity = ActivityLog(
        project_id=payload.project_id,
        entity_type="job",
        entity_id=job_id,
        action="extracted",
        description=f"Queued {payload.extraction_mode} extraction job for {len(docs)} document(s) via {payload.model or payload.pipeline_type}.",
        user="Researcher",
    )
    db.add(activity)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        run_extraction_worker,
        job_id=job.id,
        document_ids=payload.document_ids,
        pipeline_type=payload.pipeline_type,
        parameters=params,
        target_dataset_name=payload.target_dataset_name,
    )

    return job

@router.get("/jobs/{job_id}", response_model=ExtractionJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    return job

@router.post("/inspect", response_model=DocumentIntelligenceMap)
def inspect_document(document_id: str, db: Session = Depends(get_db)):
    """Deep document inspection: text density, scanned flags, table boundaries, sections, and continuation groups."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        return DocumentInspectorService.inspect_document(doc.id, doc.file_path, doc.original_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inspection failed: {e}")

@router.post("/understand", response_model=DocumentUnderstandingResponse)
def understand_document(
    document_id: str,
    provider: str = "deepseek",
    model: str = "deepseek-reasoner",
    db: Session = Depends(get_db),
):
    """Run LLM Pass 1: Document Understanding to determine document type, purpose, and dataset candidates."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_map = DocumentInspectorService.inspect_document(doc.id, doc.file_path, doc.original_name)
    page_samples = [
        {"page_number": p.page_number, "text_preview": DocumentInspectorService.get_page_text(doc.file_path, p.page_number)}
        for p in doc_map.pages[:4]
    ]
    user_prompt = document_analysis.build_document_analysis_user_prompt(
        filename=doc.original_name,
        page_count=doc_map.page_count,
        detected_sections=[s.model_dump() for s in doc_map.sections],
        detected_tables=[t.model_dump() for t in doc_map.tables],
        page_samples=page_samples,
    )
    res, _ = LLMRouter.execute_structured_with_fallback(
        schema=DocumentUnderstandingResponse,
        system_prompt=document_analysis.DOCUMENT_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        primary_provider=provider,
        primary_model=model,
    )
    return res.parsed

@router.post("/infer-schema", response_model=SchemaInferenceResponse)
def infer_schema(
    document_id: str,
    dataset_name: str,
    candidate_fields: Optional[List[str]] = None,
    provider: str = "deepseek",
    model: str = "deepseek-reasoner",
    db: Session = Depends(get_db),
):
    """Run LLM Pass 2: Schema Inference to identify field names, source labels, types, and identifiers."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_map = DocumentInspectorService.inspect_document(doc.id, doc.file_path, doc.original_name)
    sample_text = DocumentInspectorService.get_page_text(doc.file_path, 1)
    sample_rows = doc_map.tables[0].headers if doc_map.tables else []

    user_prompt = schema_analysis.build_schema_analysis_user_prompt(
        dataset_name=dataset_name,
        candidate_fields=candidate_fields or [],
        sample_pages_text=sample_text,
        sample_table_rows=[sample_rows],
    )
    res, _ = LLMRouter.execute_structured_with_fallback(
        schema=SchemaInferenceResponse,
        system_prompt=schema_analysis.SCHEMA_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        primary_provider=provider,
        primary_model=model,
    )
    return res.parsed

@router.get("/jobs/{job_id}/conflicts")
def get_job_conflicts(job_id: str, db: Session = Depends(get_db)):
    """Retrieve multi-model disagreement conflicts for a job."""
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    return job.conflicts or []

@router.post("/jobs/{job_id}/conflicts/resolve")
def resolve_job_conflict(
    job_id: str,
    payload: ResolveConflictRequest,
    db: Session = Depends(get_db),
):
    """Record human resolution for an ambiguous model conflict."""
    job = db.query(ExtractionJob).filter(ExtractionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")

    current_conflicts = list(job.conflicts or [])
    updated = False
    for c in current_conflicts:
        if c.get("id") == payload.conflict_id:
            c["resolution"] = payload.resolution
            c["resolved_value"] = payload.resolved_value
            c["resolved_by"] = payload.resolved_by
            c["comment"] = payload.comment
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Conflict record ID not found in job")

    job.conflicts = current_conflicts
    db.commit()
    return {"status": "success", "message": "Conflict resolved successfully."}
