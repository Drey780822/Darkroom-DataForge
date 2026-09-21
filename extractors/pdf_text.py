from __future__ import annotations
from typing import List, Optional, Dict
import pymupdf
from .base import BaseExtractor, ExtractionResult, RawTable


class PdfTextExtractor(BaseExtractor):
    """Reconstructs tabular structures from raw word bounding boxes and whitespace layout."""

    def __init__(self):
        super().__init__(
            name="pdf_text",
            description="Positional text layout reconstruction for borderless columnar tables"
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

                # Extract words: (x0, y0, x1, y1, word, block_no, line_no, word_no)
                words = page.get_text("words")
                if not words:
                    continue

                # Group words into horizontal lines by y-coordinate (with 3pt tolerance)
                lines_dict: Dict[int, List[tuple]] = {}
                for w in words:
                    y_key = int(round(w[1] / 4.0) * 4)
                    if y_key not in lines_dict:
                        lines_dict[y_key] = []
                    lines_dict[y_key].append(w)

                sorted_y_keys = sorted(lines_dict.keys())
                line_strings: List[List[str]] = []

                for y in sorted_y_keys:
                    row_words = sorted(lines_dict[y], key=lambda item: item[0])
                    # Join words that are closely spaced into cells
                    cells: List[str] = []
                    curr_cell: List[str] = []
                    last_x1 = -1.0

                    for w in row_words:
                        x0, _, x1, _, word = w[0], w[1], w[2], w[3], w[4]
                        # If gap between words is significant (> 18pt), treat as column break
                        if last_x1 > 0 and (x0 - last_x1) > 18.0:
                            if curr_cell:
                                cells.append(" ".join(curr_cell))
                                curr_cell = []
                        curr_cell.append(word)
                        last_x1 = x1

                    if curr_cell:
                        cells.append(" ".join(curr_cell))

                    if len(cells) >= 2:
                        line_strings.append(cells)

                if len(line_strings) >= 2:
                    # Determine modal column count
                    col_counts = [len(r) for r in line_strings]
                    modal_cols = max(set(col_counts), key=col_counts.count)
                    
                    # Keep rows matching modal count or within 1 col
                    aligned_rows = [r for r in line_strings if abs(len(r) - modal_cols) <= 1]
                    if len(aligned_rows) >= 2:
                        # Pad rows to modal_cols
                        normalized_rows = []
                        for r in aligned_rows:
                            if len(r) < modal_cols:
                                r = r + [""] * (modal_cols - len(r))
                            elif len(r) > modal_cols:
                                r = r[:modal_cols]
                            normalized_rows.append(r)

                        tables.append(
                            RawTable(
                                page_number=page_num,
                                table_index=0,
                                headers=normalized_rows[0],
                                rows=normalized_rows[1:],
                                extraction_method=self.name,
                                confidence=0.75,
                            )
                        )

            doc.close()

        except Exception as e:
            errors.append(f"Positional text extraction error: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.75 if tables else 0.15,
            warnings=warnings,
            errors=errors,
        )
