from __future__ import annotations
from typing import List, Optional
import pymupdf
from .base import BaseExtractor, ExtractionResult, RawTable


class PdfPyMuPdfExtractor(BaseExtractor):
    """High-speed vector table extractor powered by PyMuPDF's table finder."""

    def __init__(self):
        super().__init__(
            name="pdf_pymupdf",
            description="PyMuPDF high-speed table and grid extractor"
        )

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []

        try:
            doc = pymupdf.open(file_path)
            page_indices = range(len(doc)) if pages is None else [p - 1 for p in pages if 0 < p <= len(doc)]

            for p_idx in page_indices:
                page = doc[p_idx]
                page_num = p_idx + 1

                try:
                    tabs = page.find_tables()
                    for t_idx, tab in enumerate(tabs.tables):
                        df_table = tab.extract()
                        if not df_table or len(df_table) < 2:
                            continue

                        headers = [str(h).strip() if h is not None else "" for h in df_table[0]]
                        data_rows = []
                        for row in df_table[1:]:
                            cleaned_row = [str(c).strip() if c is not None else "" for c in row]
                            if any(cleaned_row):
                                data_rows.append(cleaned_row)

                        bbox = tab.bbox  # (x0, y0, x1, y1)

                        tables.append(
                            RawTable(
                                page_number=page_num,
                                table_index=t_idx,
                                headers=headers,
                                rows=data_rows,
                                extraction_method=self.name,
                                confidence=0.92,
                                bounding_box=(bbox[0], bbox[1], bbox[2], bbox[3]) if bbox else None,
                            )
                        )
                except Exception as ex:
                    warnings.append(f"Page {page_num} PyMuPDF table find error: {ex}")

            doc.close()

        except Exception as e:
            errors.append(f"PyMuPDF open failed: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.92 if tables else 0.20,
            warnings=warnings,
            errors=errors,
        )
