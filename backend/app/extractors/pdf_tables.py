from __future__ import annotations
import re
from typing import List, Optional
import pdfplumber
from backend.app.extractors.base import BaseExtractor, ExtractionResult, RawTable

class PdfTablesExtractor(BaseExtractor):
    """Extracts tables from PDFs using pdfplumber's lattice and stream algorithms."""

    def __init__(self):
        super().__init__(
            name="pdf_tables",
            description="Native PDF table parser using lattice/stream line detection"
        )

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                page_indices = range(len(pdf.pages)) if pages is None else [p - 1 for p in pages if 0 < p <= len(pdf.pages)]

                for p_idx in page_indices:
                    page = pdf.pages[p_idx]
                    page_num = p_idx + 1

                    extracted_tables = page.extract_tables()
                    if not extracted_tables:
                        extracted_tables = page.extract_tables({
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "snap_tolerance": 4,
                            "join_tolerance": 4,
                        })

                    if not extracted_tables:
                        continue

                    for t_idx, raw_table in enumerate(extracted_tables):
                        cleaned_rows: List[List[str]] = []
                        for row in raw_table:
                            if not row:
                                continue
                            cleaned_cells = [re.sub(r"[\r\n\t]+", " ", str(c)).strip() if c is not None else "" for c in row]
                            if any(cleaned_cells):
                                cleaned_rows.append(cleaned_cells)

                        if not cleaned_rows:
                            continue

                        headers: List[str] = []
                        data_rows: List[List[str]] = []

                        if len(cleaned_rows) >= 1:
                            headers = cleaned_rows[0]
                            data_rows = cleaned_rows[1:]

                        tables.append(
                            RawTable(
                                page_number=page_num,
                                table_index=t_idx,
                                headers=headers,
                                rows=data_rows,
                                extraction_method=self.name,
                                confidence=0.88,
                            )
                        )

        except Exception as e:
            errors.append(f"pdfplumber extraction failed: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.88 if tables else 0.20,
            warnings=warnings,
            errors=errors,
        )
