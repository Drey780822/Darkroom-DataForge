from backend.app.models.project import Project
from backend.app.models.document import Document
from backend.app.models.extraction_job import ExtractionJob
from backend.app.models.dataset import Dataset
from backend.app.models.record import Record
from backend.app.models.validation_issue import ValidationIssue
from backend.app.models.review import ReviewAudit
from backend.app.models.activity import ActivityLog
from backend.app.models.ai_config import AIConfig
from backend.app.models.evaluation import EvaluationRun

# Master Relational Schema Models
from backend.app.models.college import College
from backend.app.models.qualification import (
    Qualification,
    QualificationCollege,
    DsppCentreOfSpecialisation,
)
from backend.app.models.metadata import (
    DataDictionaryEntry,
    ProvenanceRecord,
    ReviewRequired,
)

__all__ = [
    "Project",
    "Document",
    "ExtractionJob",
    "Dataset",
    "Record",
    "ValidationIssue",
    "ReviewAudit",
    "ActivityLog",
    "AIConfig",
    "EvaluationRun",
    "College",
    "Qualification",
    "QualificationCollege",
    "DsppCentreOfSpecialisation",
    "DataDictionaryEntry",
    "ProvenanceRecord",
    "ReviewRequired",
]
