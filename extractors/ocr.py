from __future__ import annotations
import shutil
from typing import List, Optional
import pymupdf
from PIL import Image
import io
from .base import BaseExtractor, ExtractionResult, RawTable


class OcrExtractor(BaseExtractor):
    """Optical Character Recognition extractor using PyMuPDF pixmaps and pytesseract."""

    def __init__(self, tesseract_cmd: str = ""):
        super().__init__(
            name="ocr",
            description="Optical Character Recognition (OCR) fallback for scanned/image PDFs"
        )
        self.tesseract_cmd = tesseract_cmd

    def is_available(self) -> bool:
        if self.tesseract_cmd and shutil.which(self.tesseract_cmd):
            return True
        return shutil.which("tesseract") is not None

    def extract(self, file_path: str, pages: Optional[List[int]] = None) -> ExtractionResult:
        import pytesseract

        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        tables: List[RawTable] = []
        warnings: List[str] = []
        errors: List[str] = []

        if not self.is_available():
            warnings.append(
                "Tesseract OCR binary not detected on PATH. "
                "Scanned OCR fallback cannot execute until Tesseract-OCR is installed. "
                "Falling back to vector text extraction."
            )
            return ExtractionResult(
                tables=[],
                extraction_method=self.name,
                quality_score=0.0,
                warnings=warnings,
                errors=errors,
            )

        try:
            doc = pymupdf.open(file_path)
            page_indices = range(len(doc)) if pages is None else [p - 1 for p in pages if 0 < p <= len(doc)]

            for p_idx in page_indices:
                page = doc[p_idx]
                page_num = p_idx + 1

                # Render page to high-res pixmap (2x scale for crisp OCR)
                zoom = 2.0
                mat = pymupdf.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))

                # Run OCR with TSV output to get words and coordinates
                tsv_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DATAFRAME)
                # Clean invalid rows
                tsv_clean = tsv_data[tsv_data.text.notnull() & (tsv_data.text.str.strip() != "")]
                if tsv_clean.empty:
                    continue

                # Group by line
                lines = []
                for (block_num, line_num), line_df in tsv_clean.groupby(["block_num", "line_num"]):
                    line_words = line_df.sort_values("left")["text"].tolist()
                    if len(line_words) >= 2:
                        lines.append(line_words)

                if len(lines) >= 2:
                    tables.append(
                        RawTable(
                            page_number=page_num,
                            table_index=0,
                            headers=lines[0],
                            rows=lines[1:],
                            extraction_method=self.name,
                            confidence=0.70,
                        )
                    )

            doc.close()

        except Exception as e:
            errors.append(f"OCR execution failed: {str(e)}")

        return ExtractionResult(
            tables=tables,
            extraction_method=self.name,
            quality_score=0.70 if tables else 0.0,
            warnings=warnings,
            errors=errors,
        )
