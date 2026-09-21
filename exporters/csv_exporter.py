from __future__ import annotations
import os
from pathlib import Path
from typing import List
from models.dataset import Dataset
from .base import BaseExporter


class CsvExporter(BaseExporter):
    """Exports datasets to clean RFC 4180 CSV files with optional provenance metadata."""

    def __init__(self):
        super().__init__(name="csv", extension="csv")

    def export_dataset(
        self,
        dataset: Dataset,
        output_path: str,
        include_provenance: bool = False,
        prefer_normalized: bool = True
    ) -> str:
        df = dataset.to_pandas(prefer_normalized=prefer_normalized, include_provenance=include_provenance)
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        # Write clean CSV without pandas index
        df.to_csv(str(target), index=False, encoding="utf-8")
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
            file_path = out_dir / f"{ds.metadata.name}.csv"
            self.export_dataset(ds, str(file_path), include_provenance=include_provenance, prefer_normalized=prefer_normalized)
            paths.append(str(file_path))
        return paths
