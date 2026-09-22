import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    pipeline_type = Column(String(50), default="auto")  # qualifications, occupations, codebook, pdf_tables, auto
    extraction_mode = Column(String(50), default="high_accuracy", index=True)  # fast, balanced, high_accuracy, maximum_accuracy
    primary_model = Column(String(100), nullable=True)
    secondary_model = Column(String(100), nullable=True)
    provider = Column(String(50), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    tokens_used = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    step_status = Column(String(50), default="pending")  # inspecting, understanding, inferring_schema, extracting, validating, reconciling, completed
    conflicts = Column(JSON, default=list)  # list of ConflictRecord
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed, cancelled
    parameters = Column(JSON, default=dict)  # page_range, table_settings, ocr_mode, schema_override
    progress = Column(Integer, default=0)  # 0 to 100
    metrics = Column(JSON, default=dict)  # pages_processed, tables_found, records_count, duration_ms
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    # Relationships
    project = relationship("Project", back_populates="jobs")
    document = relationship("Document", back_populates="jobs")
    dataset = relationship("Dataset", back_populates="jobs")
