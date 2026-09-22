import os
import pytest
from pathlib import Path
from backend.app.services.document_inspector import DocumentInspectorService
from backend.app.services.chunk_manager import ChunkManagerService

SAMPLE_PDF = Path("dataforge_workspace/documents/List of Occupational Programmes updated for 2026 for website.pdf")

def test_document_inspector_real_pdf():
    if not SAMPLE_PDF.exists():
        pytest.skip("Sample PDF not present in workspace")

    doc_map = DocumentInspectorService.inspect_document(
        document_id="test-doc-1",
        file_path=str(SAMPLE_PDF),
        filename=SAMPLE_PDF.name,
    )

    assert doc_map.page_count > 0
    assert len(doc_map.pages) == doc_map.page_count
    assert doc_map.document_id == "test-doc-1"
    # Text density should be positive
    assert doc_map.text_density_avg > 0

    # Test page text extraction
    page_1_text = DocumentInspectorService.get_page_text(str(SAMPLE_PDF), 1)
    assert len(page_1_text) > 20

    # Test page image rendering
    img_bytes = DocumentInspectorService.render_page_image(str(SAMPLE_PDF), 1, dpi=72)
    assert len(img_bytes) > 1000
    assert img_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic header

def test_chunk_manager_chunking():
    if not SAMPLE_PDF.exists():
        pytest.skip("Sample PDF not present in workspace")

    doc_map = DocumentInspectorService.inspect_document(
        document_id="test-doc-1",
        file_path=str(SAMPLE_PDF),
        filename=SAMPLE_PDF.name,
    )

    chunks = ChunkManagerService.create_chunks(
        file_path=str(SAMPLE_PDF),
        doc_map=doc_map,
        pages_to_process=[1, 2, 3, 4, 5],
        chunk_size=2,
    )

    assert len(chunks) >= 2
    assert chunks[0].page_start == 1
    assert chunks[0].text is not None
    assert len(chunks[0].text) > 50
