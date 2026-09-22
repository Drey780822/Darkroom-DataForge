import re
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.activity import ActivityLog
from backend.app.models.qualification import Qualification, QualificationCollege, DsppCentreOfSpecialisation
from backend.app.models.college import College
from backend.app.models.metadata import DataDictionaryEntry, ProvenanceRecord
from backend.app.schemas.export import ExportRequest, ExportResponse
from backend.app.pipeline.exporter import DatasetExporter
from backend.app.storage.local import storage_manager

router = APIRouter(tags=["Exports"])

@router.post("/datasets/{dataset_id}/export", response_model=ExportResponse)
def export_dataset(
    dataset_id: str,
    payload: ExportRequest,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check if normalized qualifications exist for this dataset/document
    quals = db.query(Qualification).filter(Qualification.document_id == dataset.document_id).all() if dataset.document_id else []

    if quals and not payload.selected_columns:
        # Build export directly from normalized relational tables to ensure zero drift
        record_dicts = []
        for q in quals:
            coll_links = db.query(QualificationCollege).filter(QualificationCollege.saqa_id == q.saqa_id).all()
            coll_names = "; ".join([c.college_name for c in coll_links])
            dspp_links = db.query(DsppCentreOfSpecialisation).filter(DsppCentreOfSpecialisation.saqa_id == q.saqa_id).all()
            dspp_trades = "; ".join([d.programme_context for d in dspp_links])

            row_data = {
                "saqa_id": q.saqa_id,
                "qualification_number": q.qualification_number,
                "qualification_name": q.qualification_name,
                "nqf_level": q.nqf_level or "",
                "nqf_sub_framework": q.nqf_sub_framework,
                "nsfas_allowance": q.nsfas_allowance,
                "participating_colleges": coll_names,
                "dspp_programmes": dspp_trades,
                "source_section": q.source_section,
                "source_page": q.source_page,
            }
            record_dicts.append({
                "data": row_data,
                "raw_data": row_data,
                "provenance": {
                    "document_name": dataset.name,
                    "page_number": q.source_page,
                    "method": "normalized_relational_schema",
                },
                "confidence_score": 1.0 if q.confidence == "high" else (0.8 if q.confidence == "medium" else 0.5),
                "status": "valid",
            })
    else:
        query = db.query(Record).filter(Record.dataset_id == dataset_id)
        if payload.only_valid_records:
            query = query.filter(Record.status.in_(["valid", "human_reviewed"]))

        records = query.order_by(Record.row_index.asc()).all()
        record_dicts = [
            {
                "data": r.data,
                "raw_data": r.raw_data,
                "provenance": r.provenance,
                "confidence_score": r.confidence_score,
                "status": r.status,
            }
            for r in records
        ]

    export_bytes = DatasetExporter.export(
        records=record_dicts,
        format=payload.format,
        include_provenance=payload.include_provenance,
        selected_columns=payload.selected_columns,
    )

    clean_name = re.sub(r"[^\w\-_\.]", "_", dataset.name).strip("_")
    fmt = payload.format.lower().strip()
    ext = "xlsx" if fmt in ["xlsx", "excel"] else fmt
    export_filename = f"{clean_name}_{dataset.id[:8]}.{ext}"

    storage_manager.save_export_file(export_filename, export_bytes)

    activity = ActivityLog(
        project_id=dataset.project_id,
        entity_type="dataset",
        entity_id=dataset.id,
        action="exported",
        description=f"Exported dataset '{dataset.name}' to {fmt.upper()} ({len(record_dicts)} records).",
        user="Researcher",
        details={"format": fmt, "filename": export_filename, "bytes": len(export_bytes)},
    )
    db.add(activity)
    db.commit()

    return ExportResponse(
        download_url=f"/api/v1/exports/download/{export_filename}",
        filename=export_filename,
        format=fmt,
        record_count=len(record_dicts),
        file_size_bytes=len(export_bytes),
    )

@router.get("/datasets/{dataset_id}/data-dictionary", response_model=List[Dict[str, Any]])
def get_dataset_data_dictionary(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    entries = db.query(DataDictionaryEntry).filter(DataDictionaryEntry.dataset_name == dataset.name).all()
    if not entries and dataset.document_id:
        entries = db.query(DataDictionaryEntry).filter(DataDictionaryEntry.document_id == dataset.document_id).all()

    return [
        {
            "id": e.id,
            "dataset_name": e.dataset_name,
            "column_name": e.column_name,
            "data_type": e.data_type,
            "description": e.description,
            "source_field": e.source_field,
            "nullable": e.nullable,
            "example_value": e.example_value,
        }
        for e in entries
    ]

@router.get("/datasets/{dataset_id}/provenance", response_model=List[Dict[str, Any]])
def get_dataset_provenance(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    records = db.query(ProvenanceRecord).filter(ProvenanceRecord.dataset_name == dataset.name).all()
    if not records and dataset.document_id:
        records = db.query(ProvenanceRecord).filter(ProvenanceRecord.document_id == dataset.document_id).all()

    return [
        {
            "id": p.id,
            "dataset_name": p.dataset_name,
            "source_document": p.source_document,
            "source_section": p.source_section,
            "source_page": p.source_page,
            "extraction_method": p.extraction_method,
            "record_count": p.record_count,
        }
        for p in records
    ]

@router.get("/datasets/{dataset_id}/relational", response_model=List[Dict[str, Any]])
def get_dataset_relational(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.document_id:
        return []

    quals = db.query(Qualification).filter(Qualification.document_id == dataset.document_id).all()
    results = []
    for q in quals:
        colls = [
            {"college_id": qc.college_id, "college_name": qc.college_name, "section": qc.source_section}
            for qc in q.colleges
        ]
        dspp = [
            {"college_id": d.college_id, "college_name": d.college_name, "programme": d.programme_context}
            for d in q.dspp_centres
        ]
        results.append({
            "saqa_id": q.saqa_id,
            "qualification_number": q.qualification_number,
            "qualification_name": q.qualification_name,
            "nqf_level": q.nqf_level,
            "nqf_sub_framework": q.nqf_sub_framework,
            "nsfas_allowance": q.nsfas_allowance,
            "confidence": q.confidence,
            "source_section": q.source_section,
            "source_page": q.source_page,
            "colleges": colls,
            "dspp_centres": dspp,
        })
    return results

@router.get("/exports/download/{filename}")
def download_export_file(filename: str):
    target_path = storage_manager.exports_dir / filename
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    ext = target_path.suffix.lstrip(".").lower()
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=target_path,
        media_type=media_type,
        filename=filename,
    )
