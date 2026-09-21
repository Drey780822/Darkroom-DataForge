from __future__ import annotations
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from models.document import DocumentMetadata
from models.dataset import Dataset, DatasetMetadata
from models.field import FieldDefinition, DataType
from models.record import Record, CellValue
from models.validation import ValidationSummary
from models.relationship import Relationship
from models.provenance import ProvenanceRecord, RecordStatus
from storage.workspace import Workspace
from storage.project_store import ProjectStore


class ProjectMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    owner: str = "Wits–merSETA Darkroom Team"
    status: str = "Active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_count: int = 0
    version: str = "1.0.0"


class Project:
    """Represents an isolated, portable data engineering project workspace with full CRUD support."""

    def __init__(self, workspace_path: str, name: str = "New Project", description: str = ""):
        self.workspace = Workspace(workspace_path)
        self.store = ProjectStore(self.workspace)
        self.metadata = ProjectMetadata(name=name, description=description)
        self.documents: Dict[str, DocumentMetadata] = {}
        self.datasets: Dict[str, Dataset] = {}
        self.relationships: List[Relationship] = []
        self.validation_summary: Optional[ValidationSummary] = None

        if self.store.exists():
            self.load()
        else:
            self.save()

    # -------------------------------------------------------------
    # Document CRUD Operations
    # -------------------------------------------------------------
    def add_document(self, external_file_path: str, inspector=None) -> DocumentMetadata:
        copied_path = self.workspace.import_document(external_file_path)
        if inspector:
            doc_meta = inspector.create_document_metadata(copied_path)
        else:
            from core.inspector import DocumentInspector
            doc_meta = DocumentInspector().create_document_metadata(copied_path)

        self.documents[doc_meta.id] = doc_meta
        self.metadata.updated_at = datetime.now(timezone.utc)
        self.save()
        return doc_meta

    def remove_document(self, doc_id: str, delete_physical_file: bool = True) -> bool:
        """Deletes a document from the project catalog, cleaning up physical files and raw extractions."""
        if doc_id in self.documents:
            doc = self.documents[doc_id]
            if delete_physical_file:
                self.workspace.delete_document_file(doc.file_path)
                self.workspace.delete_raw_extraction(doc_id)

            del self.documents[doc_id]
            self.metadata.updated_at = datetime.now(timezone.utc)
            self.save()
            return True
        return False

    def clear_all_documents(self, delete_physical_files: bool = True) -> int:
        """Clears all ingested documents from the project."""
        count = len(self.documents)
        if delete_physical_files:
            self.workspace.clear_documents()
        self.documents.clear()
        self.metadata.updated_at = datetime.now(timezone.utc)
        self.save()
        return count

    def get_document_by_id(self, doc_id: str) -> Optional[DocumentMetadata]:
        return self.documents.get(doc_id)

    # -------------------------------------------------------------
    # Dataset CRUD Operations
    # -------------------------------------------------------------
    def create_dataset(self, name: str, columns: List[FieldDefinition], description: str = "") -> Dataset:
        """Creates an empty dataset and persists it."""
        ds = Dataset(
            metadata=DatasetMetadata(
                name=name,
                display_name=name.replace("_", " ").title(),
                description=description,
            ),
            columns=columns,
            records=[],
            primary_key=[c.name for c in columns if c.is_primary_key],
        )
        self.datasets[name] = ds
        self.store.save_datasets(list(self.datasets.values()))
        self.metadata.updated_at = datetime.now(timezone.utc)
        self.save()
        return ds

    def set_datasets(self, datasets: List[Dataset]) -> None:
        self.datasets = {ds.metadata.name: ds for ds in datasets}
        self.store.save_datasets(datasets)
        self.metadata.updated_at = datetime.now(timezone.utc)
        self.save()

    def delete_dataset(self, dataset_name: str) -> bool:
        """Deletes a dataset from the project and removes its JSON file from disk."""
        if dataset_name in self.datasets:
            del self.datasets[dataset_name]
            self.workspace.delete_dataset_file(dataset_name)
            # Remove any relationships referencing this dataset
            self.relationships = [
                r for r in self.relationships
                if r.parent_dataset != dataset_name and r.child_dataset != dataset_name
            ]
            self.store.save_datasets(list(self.datasets.values()))
            self.metadata.updated_at = datetime.now(timezone.utc)
            self.save()
            return True
        return False

    def clear_all_datasets(self) -> int:
        """Deletes all datasets from the project."""
        count = len(self.datasets)
        self.datasets.clear()
        self.relationships.clear()
        self.workspace.clear_datasets()
        self.validation_summary = None
        self.metadata.updated_at = datetime.now(timezone.utc)
        self.save()
        return count

    def add_record_to_dataset(self, dataset_name: str, values: Dict[str, Any], source_doc: str = "Manual Entry") -> Optional[Record]:
        """Appends a new record to a dataset with provenance metadata."""
        if dataset_name not in self.datasets:
            return None

        from core.normalizer import Normalizer
        ds = self.datasets[dataset_name]
        prov = ProvenanceRecord(
            source_document=source_doc,
            source_page=1,
            extraction_method="manual_entry",
            confidence=1.0,
            status=RecordStatus.HUMAN_REVIEWED,
        )
        rec = Record(provenance=prov)
        for col in ds.columns:
            val = values.get(col.name, "")
            norm_val, _ = Normalizer.normalize_value(val, field_name=col.name)
            rec.set_value(col.name, val, norm_val)

        ds.records.append(rec)
        self.store.save_datasets(list(self.datasets.values()))
        self.metadata.updated_at = datetime.now(timezone.utc)
        self.save()
        return rec

    def remove_record_from_dataset(self, dataset_name: str, record_id: str) -> bool:
        """Removes a specific record from a dataset by ID."""
        if dataset_name not in self.datasets:
            return False

        ds = self.datasets[dataset_name]
        init_len = len(ds.records)
        ds.records = [r for r in ds.records if r.id != record_id]
        if len(ds.records) < init_len:
            self.store.save_datasets(list(self.datasets.values()))
            self.metadata.updated_at = datetime.now(timezone.utc)
            self.save()
            return True
        return False

    def update_cell_value(self, dataset_name: str, record_id: str, field_name: str, new_value: Any) -> bool:
        """Updates a cell value in a record while recording human review status."""
        if dataset_name not in self.datasets:
            return False

        from core.normalizer import Normalizer
        ds = self.datasets[dataset_name]
        for rec in ds.records:
            if rec.id == record_id:
                raw_v = rec.cells[field_name].raw_value if field_name in rec.cells else new_value
                norm_val, _ = Normalizer.normalize_value(new_value, field_name=field_name)
                rec.set_value(field_name, raw_v, norm_val)
                rec.provenance.status = RecordStatus.HUMAN_REVIEWED
                rec.provenance.add_audit(f"Field '{field_name}' manually updated to '{new_value}'")
                self.store.save_datasets(list(self.datasets.values()))
                self.metadata.updated_at = datetime.now(timezone.utc)
                self.save()
                return True
        return False

    def increment_run(self) -> str:
        self.metadata.run_count += 1
        run_id = f"Run #{self.metadata.run_count:03d}"
        self.save()
        return run_id

    def save(self) -> None:
        state = {
            "metadata": self.metadata.model_dump(mode="json"),
            "documents": {k: v.model_dump(mode="json") for k, v in self.documents.items()},
            "relationships": [r.model_dump(mode="json") for r in self.relationships],
            "dataset_names": list(self.datasets.keys()),
        }
        self.store.save_project_state(state)

    def get_document_path(self, doc_id: str) -> Optional[str]:
        """Returns the resolved absolute path to the document file on the current system."""
        doc = self.documents.get(doc_id)
        if not doc:
            return None
        p = Path(doc.file_path)
        if p.exists():
            return str(p.resolve())
        candidate = (self.workspace.documents_dir / doc.filename).resolve()
        if candidate.exists():
            doc.file_path = str(candidate)
            return str(candidate)
        candidate2 = (self.workspace.documents_dir / p.name).resolve()
        if candidate2.exists():
            doc.file_path = str(candidate2)
            return str(candidate2)
        return doc.file_path

    def load(self) -> None:
        state = self.store.load_project_state()
        self.metadata = ProjectMetadata.model_validate(state["metadata"])
        self.documents = {
            k: DocumentMetadata.model_validate(v) for k, v in state.get("documents", {}).items()
        }
        # Self-heal document file paths across OS and machines
        updated_paths = False
        for doc in self.documents.values():
            p = Path(doc.file_path)
            if not p.exists():
                candidate = (self.workspace.documents_dir / doc.filename).resolve()
                if not candidate.exists():
                    candidate = (self.workspace.documents_dir / p.name).resolve()
                if candidate.exists():
                    doc.file_path = str(candidate)
                    updated_paths = True

        self.relationships = [
            Relationship.model_validate(r) for r in state.get("relationships", [])
        ]
        loaded_ds = self.store.load_datasets()
        self.datasets = {ds.metadata.name: ds for ds in loaded_ds}
        if updated_paths:
            self.save()

