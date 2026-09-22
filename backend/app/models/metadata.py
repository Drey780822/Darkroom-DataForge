from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from backend.app.database import Base

class DataDictionaryEntry(Base):
    """Data dictionary codebook defining column semantics, source headers, and data types."""
    __tablename__ = "data_dictionary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    dataset_name = Column(String, nullable=False)
    column_name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    source_field = Column(String, nullable=False)
    nullable = Column(String, nullable=False)
    example_value = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("nullable IN ('true','false')", name="chk_dict_nullable"),
        UniqueConstraint("job_id", "dataset_name", "column_name", name="uq_dict_column"),
        Index("idx_dict_job_id", "job_id"),
        Index("idx_dict_dataset_name", "dataset_name"),
    )

class ProvenanceRecord(Base):
    """Provenance tracking entry recording source document, page, and extraction methodology."""
    __tablename__ = "provenance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    dataset_name = Column(String, nullable=False)
    source_document = Column(String, nullable=False)
    source_section = Column(String, nullable=False)
    source_page = Column(String, nullable=False)
    extraction_method = Column(String, nullable=False)
    record_count = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("record_count >= 0", name="chk_provenance_record_count"),
        UniqueConstraint("job_id", "dataset_name", name="uq_prov_job_dataset"),
        Index("idx_prov_job_id", "job_id"),
        Index("idx_prov_document_id", "document_id"),
    )

class ReviewRequired(Base):
    """Human-in-the-loop review queue for values that violated validation rules or models disagreed on."""
    __tablename__ = "review_required"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    dataset_id = Column(String, ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)

    original_value = Column(String, nullable=False)
    issue = Column(String, nullable=False)
    source_page = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    agreement_score = Column(Numeric(5, 2), nullable=True)

    resolved = Column(Boolean, nullable=False, default=False)
    resolved_by = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "agreement_score IS NULL OR (agreement_score >= 0 AND agreement_score <= 100)",
            name="chk_agreement_score",
        ),
        Index("idx_rr_job_id", "job_id"),
        Index("idx_rr_document_id", "document_id"),
        Index("idx_rr_resolved", "resolved"),
    )
