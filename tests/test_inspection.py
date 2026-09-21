import pytest
import os
from pathlib import Path
from demo.sample_generator import SampleGenerator
from core.inspector import DocumentInspector


@pytest.fixture(scope="session")
def sample_tvet_pdf(tmp_path_factory):
    fn = tmp_path_factory.mktemp("pdf") / "tvet_test.pdf"
    SampleGenerator.generate_tvet_qualifications_pdf(str(fn))
    return str(fn)


def test_document_inspection(sample_tvet_pdf):
    inspector = DocumentInspector()
    result = inspector.inspect(sample_tvet_pdf)
    assert result.page_count == 2
    assert result.total_text_length > 500
    assert result.has_digital_text is True
    assert result.table_likelihood_score > 0.0
    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert result.pages[1].page_number == 2


def test_document_metadata_creation(sample_tvet_pdf):
    inspector = DocumentInspector()
    meta = inspector.create_document_metadata(sample_tvet_pdf)
    assert meta.filename == "tvet_test.pdf"
    assert meta.file_size_bytes > 1000
    assert len(meta.sha256_hash) == 64
    assert meta.inspection is not None
