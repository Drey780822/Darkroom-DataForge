from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
from models.dataset import Dataset


class BaseExporter(ABC):
    """Abstract base class for dataset exporters."""

    def __init__(self, name: str, extension: str):
        self.name = name
        self.extension = extension

    @abstractmethod
    def export_dataset(
        self,
        dataset: Dataset,
        output_path: str,
        include_provenance: bool = False,
        prefer_normalized: bool = True
    ) -> str:
        """Exports a single dataset to the target file path."""
        pass

    @abstractmethod
    def export_all(
        self,
        datasets: List[Dataset],
        output_directory: str,
        include_provenance: bool = False,
        prefer_normalized: bool = True
    ) -> List[str]:
        """Exports multiple datasets to an output directory."""
        pass
