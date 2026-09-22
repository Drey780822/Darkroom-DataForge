import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import pandas as pd

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.evaluation import EvaluationRun
from backend.app.llm.schemas import EvaluationReport
from backend.app.services.evaluation_engine import EvaluationEngineService

router = APIRouter(prefix="/evaluation", tags=["Golden Dataset Evaluation"])

@router.post("/run", response_model=EvaluationReport)
async def run_evaluation(
    dataset_id: str = Form(...),
    golden_name: Optional[str] = Form(None),
    golden_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Benchmark an extracted dataset against a Golden Ground-Truth CSV dataset."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Fetch actual records
    records = db.query(Record).filter(Record.dataset_id == dataset_id).order_by(Record.row_index.asc()).all()
    if not records:
        raise HTTPException(status_code=400, detail="Target dataset contains no extracted records to evaluate.")

    actual_data = [r.data for r in records]

    # Load golden CSV dataframe
    golden_df = None
    resolved_name = golden_name or "Uploaded Golden Dataset"

    if golden_file:
        try:
            golden_df = pd.read_csv(golden_file.file)
            resolved_name = golden_file.filename
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse uploaded golden CSV: {e}")
    else:
        # Check workspace pre-existing exports as golden benchmarks
        sample_golden_paths = [
            settings.storage_path / "exports" / "qualifications.csv",
            settings.storage_path / "exports" / "occupations_high_demand.csv",
            Path("dataforge_workspace/exports/qualifications.csv"),
            Path("dataforge_workspace/exports/occupations_high_demand.csv"),
        ]
        for p in sample_golden_paths:
            if p.exists():
                try:
                    golden_df = pd.read_csv(p)
                    resolved_name = p.name
                    break
                except Exception:
                    pass

        if golden_df is None:
            raise HTTPException(
                status_code=400,
                detail="Please upload a Golden CSV ground-truth file to benchmark this dataset against.",
            )

    report = EvaluationEngineService.evaluate(
        dataset_id=dataset_id,
        golden_df=golden_df,
        actual_records=actual_data,
        golden_name=resolved_name,
    )

    # Persist in DB
    run_entry = EvaluationRun(
        id=report.id,
        dataset_id=dataset_id,
        golden_dataset_name=report.golden_dataset_name,
        record_recall=report.record_recall,
        record_precision=report.record_precision,
        record_f1_score=report.record_f1_score,
        field_accuracy=report.field_accuracy,
        total_expected_records=report.total_expected_records,
        total_actual_records=report.total_actual_records,
        matched_records_count=report.matched_records_count,
        missing_records_count=report.missing_records_count,
        extra_records_count=report.extra_records_count,
        field_mismatches_count=report.field_mismatches_count,
        details={
            "mismatches": [m.model_dump() for m in report.mismatches[:50]],
            "missing_samples": report.missing_record_samples[:10],
            "extra_samples": report.extra_record_samples[:10],
        },
    )
    db.add(run_entry)
    db.commit()

    return report

@router.get("/runs", response_model=List[EvaluationReport])
def list_evaluation_runs(dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List historical golden dataset evaluation runs."""
    query = db.query(EvaluationRun)
    if dataset_id:
        query = query.filter(EvaluationRun.dataset_id == dataset_id)
    runs = query.order_by(EvaluationRun.created_at.desc()).all()

    return [
        EvaluationReport(
            id=r.id,
            dataset_id=r.dataset_id,
            golden_dataset_name=r.golden_dataset_name,
            evaluated_at=r.created_at.isoformat(),
            total_expected_records=r.total_expected_records,
            total_actual_records=r.total_actual_records,
            matched_records_count=r.matched_records_count,
            missing_records_count=r.missing_records_count,
            extra_records_count=r.extra_records_count,
            field_mismatches_count=r.field_mismatches_count,
            record_recall=r.record_recall,
            record_precision=r.record_precision,
            record_f1_score=r.record_f1_score,
            field_accuracy=r.field_accuracy,
            mismatches=r.details.get("mismatches", []),
            missing_record_samples=r.details.get("missing_samples", []),
            extra_record_samples=r.details.get("extra_samples", []),
        )
        for r in runs
    ]

@router.get("/runs/{run_id}", response_model=EvaluationReport)
def get_evaluation_run(run_id: str, db: Session = Depends(get_db)):
    r = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return EvaluationReport(
        id=r.id,
        dataset_id=r.dataset_id,
        golden_dataset_name=r.golden_dataset_name,
        evaluated_at=r.created_at.isoformat(),
        total_expected_records=r.total_expected_records,
        total_actual_records=r.total_actual_records,
        matched_records_count=r.matched_records_count,
        missing_records_count=r.missing_records_count,
        extra_records_count=r.extra_records_count,
        field_mismatches_count=r.field_mismatches_count,
        record_recall=r.record_recall,
        record_precision=r.record_precision,
        record_f1_score=r.record_f1_score,
        field_accuracy=r.field_accuracy,
        mismatches=r.details.get("mismatches", []),
        missing_record_samples=r.details.get("missing_samples", []),
        extra_record_samples=r.details.get("extra_samples", []),
    )
