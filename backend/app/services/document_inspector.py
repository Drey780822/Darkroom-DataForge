import os
import hashlib
import logging
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import pdfplumber

from backend.app.llm.schemas import (
    DocumentIntelligenceMap,
    PageIntelligence,
    DetectedSection,
    DetectedTable,
)

logger = logging.getLogger("dataforge.services.document_inspector")

class DocumentInspectorService:
    """Performs deep deterministic layout, table, text density, and section inspection on PDFs."""

    @classmethod
    def compute_file_hash(cls, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def inspect_document(cls, document_id: str, file_path: str, filename: str) -> DocumentIntelligenceMap:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        doc = fitz.open(file_path)
        page_count = len(doc)
        pages_intel: List[PageIntelligence] = []
        detected_tables: List[DetectedTable] = []
        detected_sections: List[DetectedSection] = []

        total_density = 0.0
        scanned_pages_count = 0

        # Pass 1: Page-level analysis via PyMuPDF
        for p_idx in range(page_count):
            page_num = p_idx + 1
            page = doc[p_idx]
            rect = page.rect
            page_area = max(1.0, rect.width * rect.height)

            text = page.get_text("text") or ""
            char_count = len(text)
            has_text = char_count > 50

            images = page.get_images(full=True)
            image_count = len(images)

            # Text density: chars per 10,000 pt²
            density = round((char_count / page_area) * 10000, 2)
            total_density += density

            # Scanned page detection: has images but negligible text layer
            is_scanned = image_count > 0 and char_count < 60
            if is_scanned:
                scanned_pages_count += 1

            # Detect running headers & footers (top/bottom 10% vertical zone)
            blocks = page.get_text("blocks") or []
            headers = []
            footers = []
            top_threshold = rect.height * 0.12
            bottom_threshold = rect.height * 0.88

            for b in blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5:
                    y0, y1, b_text = b[1], b[3], b[4].strip()
                    if not b_text:
                        continue
                    if y1 <= top_threshold and len(b_text) < 120:
                        headers.append(b_text.replace("\n", " "))
                    elif y0 >= bottom_threshold and len(b_text) < 120:
                        footers.append(b_text.replace("\n", " "))

            # Check headings (lines with larger text or uppercase keywords)
            for line in text.split("\n")[:8]:
                cleaned = line.strip()
                if cleaned and (cleaned.isupper() or cleaned.startswith("SECTION") or cleaned.startswith("TABLE") or cleaned.startswith("ANNEXURE")):
                    if len(cleaned) > 4 and len(cleaned) < 80:
                        detected_sections.append(
                            DetectedSection(
                                title=cleaned,
                                start_page=page_num,
                                end_page=page_num,
                                section_type="annexure" if "ANNEXURE" in cleaned else "dataset" if "TABLE" in cleaned else "body",
                            )
                        )

            pages_intel.append(
                PageIntelligence(
                    page_number=page_num,
                    has_text=has_text,
                    is_scanned=is_scanned,
                    text_density=density,
                    char_count=char_count,
                    table_count=0,
                    image_count=image_count,
                    headers_detected=headers[:2],
                    footers_detected=footers[:2],
                )
            )

        doc.close()

        # Pass 2: Table boundary detection via pdfplumber
        try:
            with pdfplumber.open(file_path) as plum:
                for p_idx, page in enumerate(plum.pages):
                    page_num = p_idx + 1
                    tabs = page.find_tables() or []
                    pages_intel[p_idx].table_count = len(tabs)
                    for t_idx, tab in enumerate(tabs):
                        extracted_table = tab.extract()
                        headers = [str(c or "").strip() for c in extracted_table[0]] if extracted_table else []
                        row_count = max(0, len(extracted_table) - 1) if extracted_table else 0
                        detected_tables.append(
                            DetectedTable(
                                table_id=f"tab_p{page_num}_{t_idx+1}",
                                page_number=page_num,
                                start_page=page_num,
                                end_page=page_num,
                                is_continuation=False,
                                row_count_estimate=row_count,
                                headers=headers,
                            )
                        )
        except Exception as e:
            logger.warning(f"pdfplumber table scan warning: {e}")

        # Pass 3: Detect continuation table groups across consecutive pages
        continuation_groups: List[List[int]] = []
        current_group: List[int] = []

        for i in range(len(detected_tables) - 1):
            t1 = detected_tables[i]
            t2 = detected_tables[i + 1]

            # If on adjacent pages and have similar header count or same headers
            if t2.page_number == t1.page_number + 1:
                headers_match = bool(t1.headers and t2.headers and (
                    t1.headers == t2.headers or len(t1.headers) == len(t2.headers)
                ))
                if headers_match or (t1.row_count_estimate > 5 and t2.row_count_estimate > 5):
                    t2.is_continuation = True
                    if not current_group:
                        current_group.append(t1.page_number)
                    if t2.page_number not in current_group:
                        current_group.append(t2.page_number)
                else:
                    if current_group:
                        continuation_groups.append(current_group)
                        current_group = []
            else:
                if current_group:
                    continuation_groups.append(current_group)
                    current_group = []

        if current_group:
            continuation_groups.append(current_group)

        avg_density = round(total_density / max(1, page_count), 2)
        overall_scanned = scanned_pages_count > (page_count * 0.5)

        return DocumentIntelligenceMap(
            document_id=document_id,
            filename=filename,
            page_count=page_count,
            is_scanned=overall_scanned,
            text_density_avg=avg_density,
            sections=detected_sections[:20],
            tables=detected_tables,
            pages=pages_intel,
            continuation_groups=continuation_groups,
        )

    @classmethod
    def get_page_text(cls, file_path: str, page_number: int) -> str:
        doc = fitz.open(file_path)
        if 1 <= page_number <= len(doc):
            txt = doc[page_number - 1].get_text("text") or ""
            doc.close()
            return txt
        doc.close()
        return ""

    @classmethod
    def render_page_image(cls, file_path: str, page_number: int, dpi: int = 150) -> bytes:
        doc = fitz.open(file_path)
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        doc.close()
        raise IndexError(f"Page number {page_number} out of range.")
