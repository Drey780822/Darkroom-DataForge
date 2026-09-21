import pytest
from demo.sample_generator import SampleGenerator
from core.inspector import DocumentInspector
from core.classifier import DocumentClassifier
from models.document import DocumentType


@pytest.fixture(scope="session")
def sample_documents(tmp_path_factory):
    d = tmp_path_factory.mktemp("classifier_pdfs")
    tvet_path = str(d / "DHET_TVET_Qualifications_2026.pdf")
    qlfs_path = str(d / "StatsSA_QLFS_Codebook_2026.pdf")
    oihd_path = str(d / "DHET_OIHD_National_Report_2024.pdf")

    SampleGenerator.generate_tvet_qualifications_pdf(tvet_path)
    SampleGenerator.generate_qlfs_codebook_pdf(qlfs_path)
    SampleGenerator.generate_oihd_report_pdf(oihd_path)

    return {"tvet": tvet_path, "qlfs": qlfs_path, "oihd": oihd_path}


def test_classify_tvet_qualifications(sample_documents):
    inspector = DocumentInspector()
    classifier = DocumentClassifier()
    meta = inspector.create_document_metadata(sample_documents["tvet"])
    res = classifier.classify(meta)

    assert res.document_type == DocumentType.REPEATED_TABULAR
    assert res.recommended_extractor == "qualifications"
    assert res.confidence >= 0.85


def test_classify_qlfs_codebook(sample_documents):
    inspector = DocumentInspector()
    classifier = DocumentClassifier()
    meta = inspector.create_document_metadata(sample_documents["qlfs"])
    res = classifier.classify(meta)

    assert res.document_type == DocumentType.CODEBOOK_METADATA
    assert res.recommended_extractor == "codebook"
    assert res.confidence >= 0.85


def test_classify_oihd_report(sample_documents):
    inspector = DocumentInspector()
    classifier = DocumentClassifier()
    meta = inspector.create_document_metadata(sample_documents["oihd"])
    res = classifier.classify(meta)

    assert res.document_type == DocumentType.SEMI_STRUCTURED_REPORT
    assert res.recommended_extractor == "occupations"
    assert res.confidence >= 0.85
