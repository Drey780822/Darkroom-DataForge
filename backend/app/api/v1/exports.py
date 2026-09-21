import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.activity import ActivityLog
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
        description=f"Exported dataset '{dataset.name}' to {fmt.upper()} ({len(records)} records).",
        user="Researcher",
        details={"format": fmt, "filename": export_filename, "bytes": len(export_bytes)},
    )
    db.add(activity)
    db.commit()

    return ExportResponse(
        download_url=f"/api/v1/exports/download/{export_filename}",
        filename=export_filename,
        format=fmt,
        record_count=len(records),
        file_size_bytes=len(export_bytes),
    )

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
