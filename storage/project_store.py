from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from models.document import DocumentMetadata
from models.dataset import Dataset
from models.validation import ValidationIssue, ValidationSummary
from models.relationship import Relationship
from .workspace import Workspace


class ProjectStore:
    """Handles serialization and persistence of Project configuration and state."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.project_file = self.workspace.root_path / "project.json"

    def exists(self) -> bool:
        return self.project_file.exists()

    def save_project_state(self, project_data: Dict[str, Any]) -> None:
        with open(self.project_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2, default=str)

    def load_project_state(self) -> Dict[str, Any]:
        if not self.exists():
            raise FileNotFoundError(f"No project file at {self.project_file}")
        with open(self.project_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_datasets(self, datasets: List[Dataset]) -> None:
        """Persists extracted datasets into the workspace datasets directory."""
        for ds in datasets:
            ds_file = self.workspace.datasets_dir / f"{ds.metadata.name}.json"
            with open(ds_file, "w", encoding="utf-8") as f:
                json.dump(ds.model_dump(), f, indent=2, default=str)

    def load_datasets(self) -> List[Dataset]:
        datasets: List[Dataset] = []
        if not self.workspace.datasets_dir.exists():
            return datasets
        for file_path in self.workspace.datasets_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    datasets.append(Dataset.model_validate(data))
            except Exception as e:
                print(f"Failed to load dataset {file_path}: {e}")
        return datasets
