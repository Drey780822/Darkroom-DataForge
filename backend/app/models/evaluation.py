import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    golden_dataset_name = Column(String(255), nullable=False)
    record_recall = Column(Float, default=0.0)
    record_precision = Column(Float, default=0.0)
    record_f1_score = Column(Float, default=0.0)
    field_accuracy = Column(Float, default=0.0)
    total_expected_records = Column(Integer, default=0)
    total_actual_records = Column(Integer, default=0)
    matched_records_count = Column(Integer, default=0)
    missing_records_count = Column(Integer, default=0)
    extra_records_count = Column(Integer, default=0)
    field_mismatches_count = Column(Integer, default=0)
    details = Column(JSON, default=dict)  # mismatches list, missing/extra samples
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    dataset = relationship("Dataset")
