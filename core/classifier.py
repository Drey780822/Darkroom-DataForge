from __future__ import annotations
import re
from typing import List, Tuple, Optional
from models.document import (
    DocumentMetadata,
    DocumentType,
    ClassificationResult,
    InspectionResult,
)


from core.profile_loader import ProfileLoader, get_profile_loader


class DocumentClassifier:
    """Classifies documents into archetypes and suggests optimal extraction strategies using YAML profiles."""

    def __init__(self, profile_loader: Optional[ProfileLoader] = None):
        self.profile_loader = profile_loader or get_profile_loader()

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

        # 2. Check Dynamic Profile Matches
        matched_profile = self.profile_loader.match_profile(filename, sample_corpus)
        if matched_profile:
            keywords = matched_profile.matching_patterns.get("keywords", [])
            kw_hits = [kw for kw in keywords if kw.lower() in combined_text]
            conf = min(0.98, 0.72 + (len(kw_hits) * 0.06))
            return ClassificationResult(
                document_type=matched_profile.document_type,
                confidence=round(conf, 2),
                recommended_extractor=matched_profile.recommended_extractor,
                reasons=[
                    f"Matched profile '{matched_profile.display_name}'",
                    f"Detected domain keywords: {', '.join(kw_hits[:3])}" if kw_hits else "Matched filename pattern",
                    f"Recommended extractor: {matched_profile.recommended_extractor}"
                ],
                alternative_extractors=["pdf_tables", matched_profile.recommended_extractor],
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
