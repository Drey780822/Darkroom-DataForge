import pytest
from pathlib import Path
from core.profile_loader import ProfileLoader, get_profile_loader
from core.classifier import DocumentClassifier
from core.normalizer import Normalizer
from core.project import Project
from models.document import DocumentMetadata, DocumentType, InspectionResult, PageInspection
from models.field import FieldDefinition, DataType


def test_profile_loader_discovery():
    loader = get_profile_loader()
    profiles = loader.get_all_profiles()
    assert len(profiles) >= 3

    tvet = loader.get_profile("tvet_qualifications")
    assert tvet is not None
    assert tvet.recommended_extractor == "qualifications"
    assert tvet.document_type == DocumentType.REPEATED_TABULAR

    codebook = loader.get_profile("qlfs_codebook")
    assert codebook is not None
    assert codebook.recommended_extractor == "codebook"


def test_profile_loader_matching():
    loader = get_profile_loader()

    # Match TVET by filename
    p1 = loader.match_profile("DHET_TVET_Qualifications_2026.pdf", "Sample text with SAQA ID and NQF Level")
    assert p1 is not None
    assert p1.name == "tvet_qualifications"

    # Match QLFS by keywords
    p2 = loader.match_profile("survey_2026.pdf", "variable name variable label category code Stats SA")
    assert p2 is not None
    assert p2.name == "qlfs_codebook"


def test_classifier_with_profile_loader():
    classifier = DocumentClassifier()
    page = PageInspection(page_number=1, text_length=500, sample_text="SAQA ID Qualification Title NQF Level TVET College", has_table=True)
    inspection = InspectionResult(
        page_count=5,
        total_text_length=2500,
        has_digital_text=True,
        table_likelihood_score=0.95,
        pages=[page]
    )
    doc = DocumentMetadata(
        id="doc-test-1",
        file_size_bytes=1024,
        sha256_hash="hash123",
        filename="dhet_tvet_qualifications.pdf",
        file_path="/tmp/dhet_tvet_qualifications.pdf",
        inspection=inspection
    )

    result = classifier.classify(doc)
    assert result.document_type == DocumentType.REPEATED_TABULAR
    assert result.recommended_extractor == "qualifications"
    assert result.confidence >= 0.70


def test_normalizer_provenance_clean_values():
    # Clean integer: should not be marked as modified
    val, is_mod = Normalizer.normalize_value("42", field_name="count")
    assert val == 42
    assert is_mod is False

    # Untrimmed integer: was modified
    val, is_mod = Normalizer.normalize_value("  42  ", field_name="count")
    assert val == 42
    assert is_mod is True

    # Code field with leading zero: preserved string, not marked modified if already clean
    val, is_mod = Normalizer.normalize_value("01234", field_name="ofo_code")
    assert val == "01234"
    assert is_mod is False


def test_cross_platform_path_self_healing(tmp_path):
    ws_dir = tmp_path / "test_workspace"
    docs_dir = ws_dir / "documents"
    docs_dir.mkdir(parents=True)

    # Create dummy pdf in workspace
    dummy_pdf = docs_dir / "sample_doc.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy content")

    # Initialize project
    proj = Project(str(ws_dir), name="PathTest")

    # Manually simulate a document imported on Windows with a foreign absolute path
    doc = DocumentMetadata(
        id="doc-123",
        file_size_bytes=100,
        sha256_hash="dummyhash",
        filename="sample_doc.pdf",
        file_path=r"C:\Users\OtherUser\Projects\sample_doc.pdf",
    )
    proj.documents[doc.id] = doc
    proj.save()

    # Verify file_path on disk was the Windows path
    import json
    with open(ws_dir / "project.json", "r") as f:
        data = json.load(f)
    assert r"C:\Users\OtherUser\Projects\sample_doc.pdf" in data["documents"]["doc-123"]["file_path"]

    # Re-load project on current system -> it should self-heal the path!
    proj2 = Project(str(ws_dir))
    healed_path = proj2.documents["doc-123"].file_path
    assert Path(healed_path).exists()
    assert Path(healed_path).resolve() == dummy_pdf.resolve()
