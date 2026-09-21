from __future__ import annotations
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from models.provenance import ProvenanceRecord, RecordStatus
from models.record import Record


class ProvenanceTracker:
    """Manages creation, enrichment, and verification of origin metadata for records and cells."""

    @staticmethod
    def create_provenance(
        source_document: str,
        source_page: int,
        extraction_method: str,
        confidence: float = 1.0,
        source_section: Optional[str] = None,
        source_table: Optional[str] = None,
        source_row_idx: Optional[int] = None,
    ) -> ProvenanceRecord:
        return ProvenanceRecord(
            source_document=source_document,
            source_page=source_page,
            source_section=source_section,
            source_table=source_table,
            source_row_idx=source_row_idx,
            extraction_method=extraction_method,
            extracted_at=datetime.now(timezone.utc),
            confidence=confidence,
            status=RecordStatus.SOURCE_EXTRACTED,
            audit_trail=[f"Extracted via {extraction_method} from page {source_page}"],
        )

    @staticmethod
    def mark_reviewed(record: Record, reviewer_notes: Optional[str] = None) -> None:
        record.provenance.status = RecordStatus.HUMAN_REVIEWED
        record.provenance.reviewer_notes = reviewer_notes
        record.provenance.add_audit(f"Reviewed by human operator: {reviewer_notes or 'Accepted'}")
        record.is_flagged_for_review = False

    @staticmethod
    def record_to_provenance_json(record: Record) -> Dict[str, Any]:
        return {
            "record_id": record.id,
            "provenance": record.provenance.model_dump(mode="json"),
            "modified_fields": [
                name for name, cell in record.cells.items() if cell.is_modified
            ],
        }
