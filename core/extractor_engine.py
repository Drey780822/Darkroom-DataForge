from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from extractors.base import BaseExtractor, ExtractionResult, RawTable
from extractors.pdf_tables import PdfTablesExtractor
from extractors.pdf_pymupdf import PdfPyMuPdfExtractor
from extractors.pdf_text import PdfTextExtractor
from extractors.ocr import OcrExtractor
from extractors.codebook import CodebookExtractor
from extractors.qualifications import QualificationsExtractor
from extractors.occupations import OccupationsExtractor
from .reconstructor import TableReconstructor


class ExtractionQualityScorer:
    """Calculates objective extraction quality based on measurable data integrity signals."""

    @staticmethod
    def score(result: ExtractionResult) -> float:
        if not result.tables or result.total_rows == 0:
            return 0.0

        scores: List[float] = []

        for table in result.tables:
            if not table.rows:
                continue

            expected_cols = table.column_count
            if expected_cols == 0:
                continue

            # 1. Column consistency score (rows matching expected columns)
            consistent_rows = sum(1 for r in table.rows if len(r) == expected_cols)
            col_consistency = consistent_rows / len(table.rows)

            # 2. Empty cell ratio
            total_cells = len(table.rows) * expected_cols
            empty_cells = sum(sum(1 for c in r if not str(c).strip()) for r in table.rows)
            empty_ratio = empty_cells / total_cells if total_cells > 0 else 1.0
            completeness = max(0.0, 1.0 - (empty_ratio * 1.2))

            # 3. Non-trivial content score (cells with more than 1 character)
            content_cells = sum(sum(1 for c in r if len(str(c).strip()) > 1) for r in table.rows)
            density = min(1.0, content_cells / total_cells if total_cells > 0 else 0.0)

            table_score = (col_consistency * 0.40) + (completeness * 0.35) + (density * 0.25)
            scores.append(table_score)

        return round(sum(scores) / len(scores), 2) if scores else 0.0


class ExtractorEngine:
    """Orchestrates multi-strategy extraction, quality scoring, and intelligent fallback."""

    def __init__(self, tesseract_cmd: str = ""):
        self.extractors: Dict[str, BaseExtractor] = {
            "pdf_tables": PdfTablesExtractor(),
            "pdf_pymupdf": PdfPyMuPdfExtractor(),
            "pdf_text": PdfTextExtractor(),
            "ocr": OcrExtractor(tesseract_cmd=tesseract_cmd),
            "codebook": CodebookExtractor(),
            "qualifications": QualificationsExtractor(),
            "occupations": OccupationsExtractor(),
        }
        self.reconstructor = TableReconstructor()
        self.quality_scorer = ExtractionQualityScorer()

    def get_extractor(self, name: str) -> BaseExtractor:
        return self.extractors.get(name, self.extractors["pdf_tables"])

    def extract(
        self,
        file_path: str,
        strategy: str = "pdf_tables",
        fallback_allowed: bool = True,
        min_acceptable_quality: float = 0.65
    ) -> Tuple[ExtractionResult, str]:
        """Extracts tables, attempting alternatives if quality is below threshold."""
        primary_extractor = self.get_extractor(strategy)
        result = primary_extractor.extract(file_path)
        
        # Calculate objective quality score
        result.quality_score = self.quality_scorer.score(result)
        selected_method = primary_extractor.name

        # Reconstruct tables across page boundaries
        if result.tables:
            result.tables = self.reconstructor.reconstruct(result.tables)
            result.quality_score = self.quality_scorer.score(result)

        if not fallback_allowed or result.quality_score >= min_acceptable_quality:
            return result, selected_method

        # If primary result was substandard, attempt fallbacks
        fallback_candidates = ["pdf_pymupdf", "pdf_tables", "pdf_text"]
        if strategy in fallback_candidates:
            fallback_candidates.remove(strategy)

        best_result = result
        best_method = selected_method

        for candidate_name in fallback_candidates:
            candidate_extractor = self.extractors[candidate_name]
            cand_result = candidate_extractor.extract(file_path)
            cand_result.tables = self.reconstructor.reconstruct(cand_result.tables)
            cand_result.quality_score = self.quality_scorer.score(cand_result)

            if cand_result.quality_score > best_result.quality_score:
                best_result = cand_result
                best_method = candidate_name

            if best_result.quality_score >= min_acceptable_quality:
                break

        return best_result, best_method
