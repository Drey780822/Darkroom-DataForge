from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class Qualification(Base):
    """Parent entity table representing accredited qualifications."""
    __tablename__ = "qualifications"

    saqa_id = Column(String, primary_key=True)
    qualification_number = Column(String, nullable=False)
    qualification_name = Column(String, nullable=False)
    qualification_name_raw = Column(String, nullable=False)
    nqf_level = Column(String, nullable=True)
    nqf_sub_framework = Column(String, nullable=False)
    nsfas_allowance = Column(String, nullable=False)
    source_section = Column(String, nullable=False)
    source_page = Column(String, nullable=False)
    confidence = Column(String, nullable=False)
    extraction_note = Column(String, nullable=True)

    # Cross-document/job scoping
    job_id = Column(String, ForeignKey("extraction_jobs.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        CheckConstraint("nsfas_allowance IN ('YES','NO')", name="chk_nsfas_allowance"),
        CheckConstraint("confidence IN ('high','medium','low')", name="chk_confidence"),
        CheckConstraint("nqf_sub_framework IN ('OQSF','HEQSF','GFETQSF')", name="chk_nqf_sub_framework"),
        Index("idx_qual_job_id", "job_id"),
        Index("idx_qual_document_id", "document_id"),
    )

    colleges = relationship(
        "QualificationCollege",
        back_populates="qualification",
        cascade="all, delete-orphan",
    )
    dspp_centres = relationship(
        "DsppCentreOfSpecialisation",
        back_populates="qualification",
        cascade="all, delete-orphan",
    )

class QualificationCollege(Base):
    """Junction table normalizing the 1:N relationship between qualifications and colleges."""
    __tablename__ = "qualification_colleges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    saqa_id = Column(String, ForeignKey("qualifications.saqa_id", ondelete="CASCADE"), nullable=False)
    qualification_number = Column(String, nullable=False)
    college_id = Column(String, ForeignKey("colleges.college_id", ondelete="RESTRICT"), nullable=False)
    college_name = Column(String, nullable=False)
    source_section = Column(String, nullable=False)
    source_page = Column(String, nullable=False)

    # Scoping
    job_id = Column(String, ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)

    __table_args__ = (
        UniqueConstraint("saqa_id", "college_id", name="uq_qc_pair"),
        Index("idx_qc_saqa_id", "saqa_id"),
        Index("idx_qc_college_id", "college_id"),
        Index("idx_qc_job_id", "job_id"),
    )

    qualification = relationship("Qualification", back_populates="colleges")
    college = relationship("College", back_populates="qualification_links")

class DsppCentreOfSpecialisation(Base):
    """Secondary relation table for Dual System Pilot Project (DSPP) centre affiliations."""
    __tablename__ = "dspp_centres_of_specialisation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    saqa_id = Column(String, ForeignKey("qualifications.saqa_id", ondelete="CASCADE"), nullable=False)
    qualification_number = Column(String, nullable=False)
    college_id = Column(String, ForeignKey("colleges.college_id", ondelete="RESTRICT"), nullable=False)
    college_name = Column(String, nullable=False)
    source_section = Column(String, nullable=False)
    source_page = Column(String, nullable=False)
    programme_context = Column(String, nullable=False)

    # Scoping
    job_id = Column(String, ForeignKey("extraction_jobs.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)

    __table_args__ = (
        UniqueConstraint("saqa_id", "college_id", name="uq_dspp_pair"),
        Index("idx_dspp_saqa_id", "saqa_id"),
        Index("idx_dspp_college_id", "college_id"),
        Index("idx_dspp_job_id", "job_id"),
    )

    qualification = relationship("Qualification", back_populates="dspp_centres")
    college = relationship("College", back_populates="dspp_links")
