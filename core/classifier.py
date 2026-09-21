from __future__ import annotations
import re
from typing import List, Tuple
from models.document import (
    DocumentMetadata,
    DocumentType,
    ClassificationResult,
    InspectionResult,
)


class DocumentClassifier:
    """Classifies documents into archetypes and suggests optimal extraction strategies."""

    QLFS_KEYWORDS = [
        "variable name", "variable label", "category code", "value label",
        "quarterly labour force", "stats sa", "codebook", "survey metadata"
    ]

    TVET_KEYWORDS = [
        "saqa id", "occupational certificate", "qualification title",
        "tvet college", "nqf level", "participating colleges", "oqsf", "qcto"
    ]

    OIHD_KEYWORDS = [
        "ofo code", "demand ranking", "occupations in high demand",
        "oihd", "high demand", "labour market intelligence", "critical skills"
    ]

    def classify(self, doc_metadata: DocumentMetadata) -> ClassificationResult:
        inspection = doc_metadata.inspection
        filename = doc_metadata.filename.lower()

        reasons: List[str] = []
        alt_extractors: List[str] = ["pdf_tables", "pdf_text"]

        if not inspection or inspection.page_count == 0:
            return ClassificationResult(
                document_type=DocumentType.UNSUPPORTED_AMBIGUOUS,
                confidence=0.30,
                recommended_extractor="pdf_tables",
                reasons=["Inspection data unavailable or empty document"],
                alternative_extractors=alt_extractors,
            )

        # 1. Scanned Document Check
        if inspection.scanned_pages_ratio >= 0.70 or not inspection.has_digital_text:
            return ClassificationResult(
                document_type=DocumentType.SCANNED_IMAGE,
                confidence=0.92,
                recommended_extractor="ocr",
                reasons=[
                    f"Scanned page ratio is {inspection.scanned_pages_ratio*100:.1f}%",
                    f"Digital text availability is critically low ({inspection.total_text_length} chars across {inspection.page_count} pages)"
                ],
                alternative_extractors=["pdf_tables", "ocr"],
            )

        # Gather sample text across pages
        sample_corpus = " ".join([p.sample_text.lower() for p in inspection.pages[:10]])
        combined_text = f"{filename} {sample_corpus}"

        # 2. Check for TVET Qualifications
        tvet_matches = [kw for kw in self.TVET_KEYWORDS if kw in combined_text]
        if "tvet" in filename or "saqa" in filename or len(tvet_matches) >= 2:
            conf = min(0.98, 0.70 + (len(tvet_matches) * 0.08))
            return ClassificationResult(
                document_type=DocumentType.REPEATED_TABULAR,
                confidence=round(conf, 2),
                recommended_extractor="qualifications",
                reasons=[
                    f"Detected TVET domain keywords: {', '.join(tvet_matches[:3])}",
                    f"Table likelihood is high ({inspection.table_likelihood_score*100:.0f}%)",
                    "Document structure contains repeating qualification offerings"
                ],
                alternative_extractors=["pdf_tables", "qualifications"],
            )

        # 3. Check for QLFS Codebooks
        qlfs_matches = [kw for kw in self.QLFS_KEYWORDS if kw in combined_text]
        if "qlfs" in filename or "codebook" in filename or len(qlfs_matches) >= 2:
            conf = min(0.98, 0.72 + (len(qlfs_matches) * 0.08))
            return ClassificationResult(
                document_type=DocumentType.CODEBOOK_METADATA,
                confidence=round(conf, 2),
                recommended_extractor="codebook",
                reasons=[
                    f"Detected QLFS survey/codebook terms: {', '.join(qlfs_matches[:3])}",
                    "Layout aligns with variable dictionary / value categories specification"
                ],
                alternative_extractors=["codebook", "pdf_text", "pdf_tables"],
            )

        # 4. Check for Occupations in High Demand (OIHD)
        oihd_matches = [kw for kw in self.OIHD_KEYWORDS if kw in combined_text]
        if "oihd" in filename or "demand" in filename or len(oihd_matches) >= 2:
            conf = min(0.95, 0.68 + (len(oihd_matches) * 0.09))
            return ClassificationResult(
                document_type=DocumentType.SEMI_STRUCTURED_REPORT,
                confidence=round(conf, 2),
                recommended_extractor="occupations",
                reasons=[
                    f"Detected OIHD labour market terms: {', '.join(oihd_matches[:3])}",
                    "Structure indicates narrative research report with embedded annexure tables"
                ],
                alternative_extractors=["occupations", "pdf_tables"],
            )

        # 5. Generic Structured Table PDF
        if inspection.table_likelihood_score >= 0.50:
            doc_type = DocumentType.STRUCTURED_TABLE
            if inspection.page_count > 3:
                doc_type = DocumentType.REPEATED_TABULAR
            return ClassificationResult(
                document_type=doc_type,
                confidence=0.85,
                recommended_extractor="pdf_tables",
                reasons=[
                    f"Consistent tabular alignment detected across pages ({inspection.table_likelihood_score*100:.0f}% likelihood)",
                    "Digital vector lines and grid bounding boxes present"
                ],
                alternative_extractors=["pdf_tables", "pdf_text"],
            )

        # 6. Semi-Structured Report
        if inspection.text_availability_score >= 0.60:
            return ClassificationResult(
                document_type=DocumentType.SEMI_STRUCTURED_REPORT,
                confidence=0.75,
                recommended_extractor="pdf_tables",
                reasons=[
                    "Substantial narrative text content with intermittent tabular sections",
                    "Recommended table extraction with text layout fallback"
                ],
                alternative_extractors=["pdf_tables", "pdf_text"],
            )

        # 7. Fallback / Mixed
        return ClassificationResult(
            document_type=DocumentType.MIXED_DOCUMENT,
            confidence=0.60,
            recommended_extractor="pdf_tables",
            reasons=["Mixed text and visual layout; default tabular extractor selected"],
            alternative_extractors=["pdf_tables", "pdf_text", "ocr"],
        )
