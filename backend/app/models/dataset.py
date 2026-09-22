import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    schema_name = Column(String(100), default="generic", index=True)  # qualifications, occupations, codebook, generic
    schema_columns = Column(JSON, default=list)  # list of {name, type, required, description}
    record_count = Column(Integer, default=0)
    valid_record_count = Column(Integer, default=0)
    warning_record_count = Column(Integer, default=0)
    error_record_count = Column(Integer, default=0)
    quality_score = Column(Float, default=100.0)  # 0.0 - 100.0
    status = Column(String(50), default="raw", index=True)  # raw, normalized, validated, reviewed, published
    is_verified = Column(Boolean, default=False, index=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_notes = Column(Text, nullable=True)
    data_dictionary = Column(JSON, default=list)  # list of {dataset_name, column_name, source_label, data_type, nullable, description, identifier, example_value, source_pages}
    document_map = Column(JSON, default=dict)  # sections, detected tables, metadata
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    project = relationship("Project", back_populates="datasets")
    document = relationship("Document", back_populates="datasets")
    records = relationship("Record", back_populates="dataset", cascade="all, delete-orphan")
    validation_issues = relationship("ValidationIssue", back_populates="dataset", cascade="all, delete-orphan")
    jobs = relationship("ExtractionJob", back_populates="dataset")
