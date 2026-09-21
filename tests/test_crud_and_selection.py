import pytest
import os
from pathlib import Path
from demo.sample_generator import SampleGenerator
from core.project import Project
from core.pipeline import DataforgePipeline, StageStatus
from models.field import FieldDefinition, DataType
from models.provenance import RecordStatus


@pytest.fixture
def temp_project(tmp_path):
    ws_dir = tmp_path / "test_workspace"
    proj = Project(workspace_path=str(ws_dir), name="Test_CRUD_Project")
    return proj


@pytest.fixture
def two_test_pdfs(tmp_path):
    p1 = tmp_path / "tvet_doc.pdf"
    p2 = tmp_path / "qlfs_doc.pdf"
    SampleGenerator.generate_tvet_qualifications_pdf(str(p1))
    SampleGenerator.generate_qlfs_codebook_pdf(str(p2))
    return str(p1), str(p2)


def test_document_crud_and_physical_cleanup(temp_project, two_test_pdfs):
    pdf1, pdf2 = two_test_pdfs
    
    # 1. Ingest documents
    doc1 = temp_project.add_document(pdf1)
    doc2 = temp_project.add_document(pdf2)
    assert len(temp_project.documents) == 2
    assert Path(doc1.file_path).exists()
    assert Path(doc2.file_path).exists()

    # 2. Delete single document
    doc1_id = doc1.id
    doc1_file = doc1.file_path
    success = temp_project.remove_document(doc1_id, delete_physical_file=True)
    assert success is True
    assert doc1_id not in temp_project.documents
    assert not Path(doc1_file).exists()
    assert len(temp_project.documents) == 1

    # Reload project to verify state persistence
    reloaded_proj = Project(workspace_path=temp_project.workspace.root, name="Test_CRUD_Project")
    assert len(reloaded_proj.documents) == 1
    assert doc1_id not in reloaded_proj.documents

    # 3. Clear all documents
    cleared_count = temp_project.clear_all_documents(delete_physical_files=True)
    assert cleared_count == 1
    assert len(temp_project.documents) == 0
    assert not Path(doc2.file_path).exists()


def test_selective_pipeline_execution(temp_project, two_test_pdfs):
    pdf1, pdf2 = two_test_pdfs
    doc1 = temp_project.add_document(pdf1)
    doc2 = temp_project.add_document(pdf2)
    assert len(temp_project.documents) == 2

    pipeline = DataforgePipeline(temp_project)

    # Execute pipeline on ONLY document 1 (TVET)
    result = pipeline.run_pipeline(document_ids=[doc1.id])
    assert result.overall_status in [StageStatus.COMPLETE, StageStatus.WARNING]
    
    # Only TVET dataset(s) should be generated
    dataset_names = list(temp_project.datasets.keys())
    assert any("qualifications" in name for name in dataset_names)
    assert not any("qlfs" in name for name in dataset_names)

    # Now execute pipeline on document 2 (QLFS)
    result2 = pipeline.run_pipeline(document_ids=[doc2.id])
    assert result2.overall_status in [StageStatus.COMPLETE, StageStatus.WARNING]

    # Both datasets should now exist without overwriting the previous run
    dataset_names_after = list(temp_project.datasets.keys())
    assert any("qualifications" in name for name in dataset_names_after)
    assert any("qlfs" in name for name in dataset_names_after)


def test_dataset_crud_and_cell_editing(temp_project):
    # 1. Create a dataset manually
    cols = [
        FieldDefinition(name="code", display_name="Code", data_type=DataType.STRING, is_primary_key=True),
        FieldDefinition(name="title", display_name="Title", data_type=DataType.STRING),
        FieldDefinition(name="province", display_name="Province", data_type=DataType.STRING),
    ]
    ds = temp_project.create_dataset(name="custom_occupations", columns=cols, description="Custom test dataset")
    assert "custom_occupations" in temp_project.datasets
    assert ds.record_count == 0

    # 2. Add records
    rec1 = temp_project.add_record_to_dataset(
        "custom_occupations",
        {"code": "651202", "title": "Welder", "province": "GP"}
    )
    assert rec1 is not None
    assert rec1.cells["code"].normalized_value == "651202"
    assert rec1.cells["province"].normalized_value == "Gauteng"  # Standardized province!
    assert rec1.provenance.status == RecordStatus.HUMAN_REVIEWED

    rec2 = temp_project.add_record_to_dataset(
        "custom_occupations",
        {"code": "671101", "title": "Electrician", "province": "KZN"}
    )
    assert temp_project.datasets["custom_occupations"].record_count == 2

    # 3. Edit a cell value
    edit_success = temp_project.update_cell_value(
        "custom_occupations",
        rec1.id,
        "title",
        "Master Welder"
    )
    assert edit_success is True
    updated_rec = [r for r in temp_project.datasets["custom_occupations"].records if r.id == rec1.id][0]
    assert updated_rec.cells["title"].normalized_value == "Master Welder"
    assert any("Master Welder" in a for a in updated_rec.provenance.audit_log)

    # 4. Remove a record
    del_rec_success = temp_project.remove_record_from_dataset("custom_occupations", rec2.id)
    assert del_rec_success is True
    assert temp_project.datasets["custom_occupations"].record_count == 1

    # 5. Delete dataset
    del_ds_success = temp_project.delete_dataset("custom_occupations")
    assert del_ds_success is True
    assert "custom_occupations" not in temp_project.datasets

    # 6. Clear all datasets
    temp_project.create_dataset(name="ds_a", columns=cols)
    temp_project.create_dataset(name="ds_b", columns=cols)
    assert len(temp_project.datasets) == 2
    cleared = temp_project.clear_all_datasets()
    assert cleared == 2
    assert len(temp_project.datasets) == 0
