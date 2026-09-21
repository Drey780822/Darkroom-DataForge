from __future__ import annotations
import json
from pathlib import Path
from typing import List
from models.dataset import Dataset
from .base import BaseExporter


class JsonExporter(BaseExporter):
    """Exports datasets to formatted JSON or JSON-Lines documents."""

    def __init__(self, indent: int = 2):
        super().__init__(name="json", extension="json")
        self.indent = indent

    def export_dataset(
        self,
        dataset: Dataset,
        output_path: str,
        include_provenance: bool = False,
        prefer_normalized: bool = True
    ) -> str:
        records_data = [
            r.to_dict(prefer_normalized=prefer_normalized, include_provenance=include_provenance)
            for r in dataset.records
        ]
        doc = {
            "metadata": dataset.metadata.model_dump(mode="json"),
            "columns": [c.model_dump(mode="json") for c in dataset.columns],
            "record_count": len(records_data),
            "records": records_data,
        }

        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=self.indent, default=str)
        return str(target)

    def export_all(
        self,
        datasets: List[Dataset],
        output_directory: str,
        include_provenance: bool = False,
        prefer_normalized: bool = True
    ) -> List[str]:
        out_dir = Path(output_directory).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: List[str] = []
        for ds in datasets:
            file_path = out_dir / f"{ds.metadata.name}.json"
            self.export_dataset(ds, str(file_path), include_provenance=include_provenance, prefer_normalized=prefer_normalized)
            paths.append(str(file_path))
        return paths
