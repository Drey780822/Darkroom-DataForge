from __future__ import annotations
import os
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List


class Workspace:
    """Manages the physical on-disk project directory hierarchy and file artifacts."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
        self.documents_dir = self.root_path / "documents"
        self.raw_dir = self.root_path / "raw"
        self.extracted_dir = self.root_path / "extracted"
        self.datasets_dir = self.root_path / "datasets"
        self.validation_dir = self.root_path / "validation"
        self.exports_dir = self.root_path / "exports"
        self.logs_dir = self.root_path / "logs"
        self.init_directories()

    @property
    def root(self) -> str:
        return str(self.root_path)

    def init_directories(self) -> None:
        for directory in [
            self.root_path,
            self.documents_dir,
            self.raw_dir,
            self.extracted_dir,
            self.datasets_dir,
            self.validation_dir,
            self.exports_dir,
            self.logs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def import_document(self, source_file_path: str) -> str:
        """Copies an external PDF into the project's documents directory."""
        src = Path(source_file_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")
        
        dest = self.documents_dir / src.name
        # If file already exists with same name, make it unique
        if dest.exists() and dest.resolve() != src:
            stem = src.stem
            suffix = src.suffix
            counter = 1
            while dest.exists():
                dest = self.documents_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        
        if dest.resolve() != src:
            shutil.copy2(str(src), str(dest))
        return str(dest)

    def delete_document_file(self, filename: str) -> bool:
        """Deletes a physical document file from the workspace documents directory."""
        target = self.documents_dir / Path(filename).name
        if target.exists():
            try:
                target.unlink()
                return True
            except Exception:
                pass
        return False

    def delete_raw_extraction(self, doc_id: str) -> bool:
        """Deletes raw extraction JSON for a document."""
        target = self.raw_dir / f"{doc_id}_raw.json"
        if target.exists():
            try:
                target.unlink()
                return True
            except Exception:
                pass
        return False

    def delete_dataset_file(self, dataset_name: str) -> bool:
        """Deletes a dataset JSON file from datasets directory."""
        target = self.datasets_dir / f"{dataset_name}.json"
        if target.exists():
            try:
                target.unlink()
                return True
            except Exception:
                pass
        return False

    def clear_documents(self) -> int:
        """Removes all files in documents/ and raw/ directories."""
        count = 0
        for f in self.documents_dir.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                    count += 1
                except Exception:
                    pass
        for f in self.raw_dir.glob("*"):
            if f.is_file():
                try:
                    f.unlink()
                except Exception:
                    pass
        return count

    def clear_datasets(self) -> int:
        """Removes all dataset JSON files from datasets/."""
        count = 0
        for f in self.datasets_dir.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
        return count

    def save_raw_extraction(self, doc_id: str, raw_data: Dict[str, Any]) -> str:
        out_path = self.raw_dir / f"{doc_id}_raw.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, default=str)
        return str(out_path)

    def load_raw_extraction(self, doc_id: str) -> Optional[Dict[str, Any]]:
        target = self.raw_dir / f"{doc_id}_raw.json"
        if not target.exists():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_validation_report(self, report_data: Dict[str, Any]) -> str:
        out_path = self.validation_dir / "validation_report.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        return str(out_path)

    def save_manifest(self, manifest_data: Dict[str, Any]) -> str:
        out_path = self.root_path / "manifest.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, default=str)
        return str(out_path)

    def get_log_file(self) -> str:
        return str(self.logs_dir / "pipeline.log")
