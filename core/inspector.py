from __future__ import annotations
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymupdf  # PyMuPDF
from models.document import (
    DocumentMetadata,
    InspectionResult,
    PageInspection,
    DocumentStatus,
)


class DocumentInspector:
    """Performs deep forensic inspection of PDF files to evaluate structure and characteristics."""

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def inspect(self, file_path: str, max_inspect_pages: int = 50) -> InspectionResult:
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        doc = pymupdf.open(str(path))
        page_count = len(doc)
        total_text_length = 0
        total_images = 0
        scanned_pages_count = 0
        detected_tables_count = 0
        pages_to_scan = min(page_count, max_inspect_pages)

        page_inspections: List[PageInspection] = []

        for page_idx in range(pages_to_scan):
            page = doc[page_idx]
            text = page.get_text("text") or ""
            text_len = len(text.strip())
            words = text.split()
            word_count = len(words)
            total_text_length += text_len

            images = page.get_images()
            image_count = len(images)
            total_images += image_count

            # Heuristic for scanned page: very few or no characters, but contains images
            is_scanned = (text_len < 40 and image_count > 0)
            if is_scanned:
                scanned_pages_count += 1

            # Detect drawings/vector lines which indicate bordered tables
            drawings = page.get_drawings()
            has_vectors = len(drawings) > 0
            
            # Table detection heuristic:
            # High line count OR presence of tabs/multiple column alignments
            has_tables = False
            table_count = 0
            try:
                tables = page.find_tables()
                if tables and len(tables.tables) > 0:
                    has_tables = True
                    table_count = len(tables.tables)
                    detected_tables_count += table_count
            except Exception:
                # Fallback heuristic if find_tables is unavailable
                has_tables = (len(drawings) > 8 and word_count > 15)
                if has_tables:
                    table_count = 1
                    detected_tables_count += 1

            sample_snippet = text[:200].replace("\n", " ").strip()

            page_inspections.append(
                PageInspection(
                    page_number=page_idx + 1,
                    text_length=text_len,
                    word_count=word_count,
                    image_count=image_count,
                    has_tables=has_tables,
                    table_count=table_count,
                    is_scanned_likely=is_scanned,
                    has_vector_graphics=has_vectors,
                    sample_text=sample_snippet,
                )
            )

        doc_metadata = doc.metadata or {}
        doc.close()

        scanned_ratio = scanned_pages_count / pages_to_scan if pages_to_scan > 0 else 0.0
        avg_text_per_page = total_text_length / pages_to_scan if pages_to_scan > 0 else 0
        text_availability = min(1.0, avg_text_per_page / 300.0)
        table_likelihood = min(1.0, (detected_tables_count / pages_to_scan) if pages_to_scan > 0 else 0.0)

        return InspectionResult(
            page_count=page_count,
            total_text_length=total_text_length,
            total_images=total_images,
            scanned_pages_ratio=round(scanned_ratio, 2),
            text_availability_score=round(text_availability, 2),
            table_likelihood_score=round(table_likelihood, 2),
            has_digital_text=(total_text_length > 100),
            metadata=doc_metadata,
            pages=page_inspections,
        )

    def create_document_metadata(self, file_path: str, doc_id: Optional[str] = None) -> DocumentMetadata:
        path = Path(file_path).resolve()
        import uuid
        did = doc_id or str(uuid.uuid4())
        size = path.stat().st_size
        sha = self.compute_sha256(str(path))
        
        inspection = self.inspect(str(path))
        
        return DocumentMetadata(
            id=did,
            filename=path.name,
            file_path=str(path),
            file_size_bytes=size,
            sha256_hash=sha,
            status=DocumentStatus.INSPECTED,
            inspection=inspection,
        )
