from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.dataset import Dataset
from backend.app.models.activity import ActivityLog
from backend.app.schemas.dataset import DatasetResponse, DatasetUpdate, VerifyDatasetRequest

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.get("", response_model=List[DatasetResponse])
def list_datasets(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Dataset)
    if project_id:
        query = query.filter(Dataset.project_id == project_id)
    return query.order_by(Dataset.created_at.desc()).all()

@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.patch("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(dataset_id: str, payload: DatasetUpdate, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if payload.name is not None:
        dataset.name = payload.name
    if payload.description is not None:
        dataset.description = payload.description
    if payload.status is not None:
        dataset.status = payload.status

    db.commit()
    db.refresh(dataset)
    return dataset

@router.post("/{dataset_id}/verify", response_model=DatasetResponse)
def verify_dataset(dataset_id: str, payload: VerifyDatasetRequest, db: Session = Depends(get_db)):
    """Mark a dataset as Verified after human review and provenance inspection."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset.is_verified = True
    dataset.verified_by = payload.verified_by
    dataset.verified_at = datetime.now(timezone.utc)
    dataset.verification_notes = payload.verification_notes
    dataset.status = "reviewed"

    activity = ActivityLog(
        project_id=dataset.project_id,
        entity_type="dataset",
        entity_id=dataset.id,
        action="reviewed",
        description=f"Researcher '{payload.verified_by}' verified dataset '{dataset.name}'. Notes: {payload.verification_notes or 'None'}",
        user=payload.verified_by,
    )
    db.add(activity)
    db.commit()
    db.refresh(dataset)
    return dataset

@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    activity = ActivityLog(
        project_id=dataset.project_id,
        entity_type="dataset",
        entity_id=dataset.id,
        action="deleted",
        description=f"Deleted dataset '{dataset.name}' and all its records.",
        user="Researcher",
    )
    db.add(activity)

    db.delete(dataset)
    db.commit()
    return None

@router.get("/{dataset_id}/relational-stats")
def get_dataset_relational_stats(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    from backend.app.models.qualification import Qualification, QualificationCollege, DsppCentreOfSpecialisation
    from backend.app.models.metadata import ReviewRequired

    quals_count = 0
    colleges_linked = 0
    dspp_count = 0
    review_count = 0

    if dataset.document_id:
        quals_count = db.query(Qualification).filter(Qualification.document_id == dataset.document_id).count()
        colleges_linked = db.query(QualificationCollege).filter(QualificationCollege.document_id == dataset.document_id).count()
        dspp_count = db.query(DsppCentreOfSpecialisation).filter(DsppCentreOfSpecialisation.document_id == dataset.document_id).count()
        review_count = db.query(ReviewRequired).filter(ReviewRequired.document_id == dataset.document_id).count()

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "record_count": dataset.record_count,
        "qualifications_count": quals_count,
        "colleges_linked_count": colleges_linked,
        "dspp_centres_count": dspp_count,
        "review_required_count": review_count,
    }
