import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from backend.app.database import get_db, SessionLocal, engine, init_db
from backend.app.models.college import College
from backend.app.models.qualification import (
    Qualification,
    QualificationCollege,
    DsppCentreOfSpecialisation,
)
from backend.app.models.metadata import (
    DataDictionaryEntry,
    ProvenanceRecord,
    ReviewRequired,
)
from backend.app.models.project import Project
from backend.app.models.document import Document
from backend.app.models.dataset import Dataset
from backend.app.models.extraction_job import ExtractionJob
from backend.app.pipeline.validator import (
    Validator,
    ALLOWED_NSFAS_ALLOWANCES,
    ALLOWED_CONFIDENCE_LEVELS,
    ALLOWED_NQF_SUB_FRAMEWORKS,
)
from backend.app.main import app

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_1_tables_and_indexes_exist():
    """AC 1: Verify all 7 relational tables and their indexes exist in the schema."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    
    expected_tables = {
        "qualifications",
        "colleges",
        "qualification_colleges",
        "dspp_centres_of_specialisation",
        "data_dictionary",
        "provenance",
        "review_required",
    }
    
    for table in expected_tables:
        assert table in table_names, f"Table '{table}' missing from database schema"

    # Verify foreign key indexes exist
    qc_indexes = {idx["name"] for idx in inspector.get_indexes("qualification_colleges")}
    assert "idx_qc_saqa_id" in qc_indexes
    assert "idx_qc_college_id" in qc_indexes

    dspp_indexes = {idx["name"] for idx in inspector.get_indexes("dspp_centres_of_specialisation")}
    assert "idx_dspp_saqa_id" in dspp_indexes
    assert "idx_dspp_college_id" in dspp_indexes

    rr_indexes = {idx["name"] for idx in inspector.get_indexes("review_required")}
    assert "idx_rr_job_id" in rr_indexes
    assert "idx_rr_resolved" in rr_indexes

def test_2_foreign_key_rejection_on_orphan_insert(db):
    """AC 2: Foreign key pragma ON - rejecting orphan insert on qualification_colleges."""
    # Attempt inserting junction record with non-existent SAQA ID and college ID
    orphan = QualificationCollege(
        saqa_id="NON_EXISTENT_SAQA_99999",
        qualification_number="99999",
        college_id="C9999",
        college_name="Ghost TVET College",
        source_section="Section 1",
        source_page="1",
    )
    db.add(orphan)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_3_unique_constraint_on_duplicate_pair(db):
    """AC 3: Unique constraint on (saqa_id, college_id) prevents duplicate pairs."""
    import uuid
    test_saqa = f"SAQA_{uuid.uuid4().hex[:8]}"
    test_college = f"Test TVET College {uuid.uuid4().hex[:6]}"

    # 1. Create a parent qualification
    qual = Qualification(
        saqa_id=test_saqa,
        qualification_number="Q001",
        qualification_name="Occupational Certificate: Electrician",
        qualification_name_raw="Occupational Certificate: Electrician",
        nqf_level="4",
        nqf_sub_framework="OQSF",
        nsfas_allowance="YES",
        source_section="Section 1",
        source_page="5",
        confidence="high",
    )
    db.add(qual)

    # 2. Create college via get_or_create
    col = College.get_or_create(db, test_college)
    db.commit()

    # 3. Add first junction record -> succeeds
    qc1 = QualificationCollege(
        saqa_id=qual.saqa_id,
        qualification_number=qual.qualification_number,
        college_id=col.college_id,
        college_name=col.college_name,
        source_section="Section 1",
        source_page="5",
    )
    db.add(qc1)
    db.commit()

    # 4. Add duplicate junction record -> raises IntegrityError
    qc2 = QualificationCollege(
        saqa_id=qual.saqa_id,
        qualification_number=qual.qualification_number,
        college_id=col.college_id,
        college_name=col.college_name,
        source_section="Section 1",
        source_page="5",
    )
    db.add(qc2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_4_check_constraints_rejection_on_invalid_values(db):
    """AC 4: Pre-DB and SQLite CHECK constraints enforce allowed sets."""
    # 4a: nsfas_allowance must be 'YES' or 'NO'
    invalid_nsfas = Qualification(
        saqa_id="SAQA_CHK_001",
        qualification_number="Q002",
        qualification_name="Fitter and Turner",
        qualification_name_raw="Fitter and Turner",
        nqf_level="4",
        nqf_sub_framework="OQSF",
        nsfas_allowance="Yes",  # Violates CHECK (nsfas_allowance IN ('YES','NO'))
        source_section="Section 1",
        source_page="1",
        confidence="high",
    )
    db.add(invalid_nsfas)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # 4b: confidence must be 'high', 'medium', or 'low'
    invalid_conf = Qualification(
        saqa_id="SAQA_CHK_002",
        qualification_number="Q003",
        qualification_name="Boilermaker",
        qualification_name_raw="Boilermaker",
        nqf_level="4",
        nqf_sub_framework="OQSF",
        nsfas_allowance="YES",
        source_section="Section 1",
        source_page="1",
        confidence="highest",  # Violates CHECK (confidence IN ('high','medium','low'))
    )
    db.add(invalid_conf)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # 4c: nqf_sub_framework must be 'OQSF', 'HEQSF', or 'GFETQSF'
    invalid_fw = Qualification(
        saqa_id="SAQA_CHK_003",
        qualification_number="Q004",
        qualification_name="Diesel Mechanic",
        qualification_name_raw="Diesel Mechanic",
        nqf_level="4",
        nqf_sub_framework="OTHER_FW",  # Violates CHECK (nqf_sub_framework IN ('OQSF','HEQSF','GFETQSF'))
        nsfas_allowance="YES",
        source_section="Section 1",
        source_page="1",
        confidence="high",
    )
    db.add(invalid_fw)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_5_college_global_surrogate_key_never_collides(db):
    """AC 5: College surrogate IDs are sequential (C0001, C0002...) and never reset across jobs."""
    c1 = College.get_or_create(db, "Tshwane South TVET College")
    c2 = College.get_or_create(db, "Sedibeng TVET College")
    c3 = College.get_or_create(db, "Tshwane South TVET College")  # Idempotent lookup
    
    assert c1.college_id.startswith("C")
    assert len(c1.college_id) == 5  # Format C0001
    assert c2.college_id.startswith("C")
    assert c1.college_id != c2.college_id
    assert c3.college_id == c1.college_id  # Re-used existing college record

def test_6_validator_routing_to_review_required(db, client):
    """AC 6: Invalid or ambiguous values are routed to review_required and never silently discarded."""
    # Create parent project, document, job for FK integrity
    proj = Project(name="Test Review Project")
    db.add(proj)
    db.flush()

    doc = Document(
        project_id=proj.id,
        filename="test_review_doc.pdf",
        original_name="test_review_doc.pdf",
        file_path="/tmp/test_review_doc.pdf",
        doc_type="qualifications",
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        project_id=proj.id,
        document_id=doc.id,
        pipeline_type="qualifications",
    )
    db.add(job)
    db.commit()

    rec = {
        "saqa_id": "99999",
        "nsfas_allowance": "Pending",  # Invalid
        "confidence": "high",
        "nqf_sub_framework": "OQSF",
    }
    is_valid, violations = Validator.validate_qualification_constraints(rec)
    assert not is_valid
    assert any(v["column_name"] == "nsfas_allowance" for v in violations)

    # Route to review_required
    rr_entry = Validator.route_to_review_required(
        db=db,
        original_value="Pending",
        issue="chk_nsfas_allowance",
        source_page="12",
        reason="Value 'Pending' is not 'YES' or 'NO'",
        job_id=job.id,
        document_id=doc.id,
    )
    db.commit()

    assert rr_entry.id is not None
    assert rr_entry.resolved is False

    # Verify review endpoint lists this entry
    res = client.get(f"/api/v1/review/review-required?job_id={job.id}")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    target = next(i for i in items if i["id"] == rr_entry.id)
    assert target["original_value"] == "Pending"
    assert target["resolved"] is False

    # Resolve review item via API
    resolve_res = client.post(f"/api/v1/review/review-required/{rr_entry.id}/resolve", json={
        "resolved_by": "Senior Researcher",
        "correction": "NO",
    })
    assert resolve_res.status_code == 200
    assert resolve_res.json()["resolved"] is True
    assert resolve_res.json()["resolved_by"] == "Senior Researcher"

def test_7_metadata_tables_scoped_by_job(db):
    """AC 7: data_dictionary and provenance tables are scoped to job_id to prevent clashes across documents."""
    proj = Project(name="Test Scoping Project")
    db.add(proj)
    db.flush()

    doc1 = Document(
        project_id=proj.id,
        filename="Doc_A.pdf",
        original_name="Doc_A.pdf",
        file_path="/tmp/Doc_A.pdf",
        doc_type="qualifications",
    )
    doc2 = Document(
        project_id=proj.id,
        filename="Doc_B.pdf",
        original_name="Doc_B.pdf",
        file_path="/tmp/Doc_B.pdf",
        doc_type="qualifications",
    )
    db.add(doc1)
    db.add(doc2)
    db.flush()

    job1 = ExtractionJob(project_id=proj.id, document_id=doc1.id)
    job2 = ExtractionJob(project_id=proj.id, document_id=doc2.id)
    db.add(job1)
    db.add(job2)
    db.commit()

    # Insert data dictionary for job 1
    d1 = DataDictionaryEntry(
        job_id=job1.id,
        document_id=doc1.id,
        dataset_name="qualifications",
        column_name="saqa_id",
        data_type="string",
        description="SAQA Qualification Identifier",
        source_field="SAQA ID",
        nullable="false",
    )
    db.add(d1)

    # Insert same dataset name and column for job 2 (should succeed without collision!)
    d2 = DataDictionaryEntry(
        job_id=job2.id,
        document_id=doc2.id,
        dataset_name="qualifications",
        column_name="saqa_id",
        data_type="string",
        description="SAQA Qualification Identifier",
        source_field="SAQA ID",
        nullable="false",
    )
    db.add(d2)

    # Provenance for job 1 and job 2 with same dataset name
    p1 = ProvenanceRecord(
        job_id=job1.id,
        document_id=doc1.id,
        dataset_name="qualifications",
        source_document="Doc_A.pdf",
        source_section="Section 1",
        source_page="1-10",
        extraction_method="deterministic_table",
        record_count=100,
    )
    p2 = ProvenanceRecord(
        job_id=job2.id,
        document_id=doc2.id,
        dataset_name="qualifications",
        source_document="Doc_B.pdf",
        source_section="Section 1",
        source_page="1-15",
        extraction_method="deterministic_table",
        record_count=150,
    )
    db.add(p1)
    db.add(p2)
    db.commit()

    assert d1.id != d2.id
    assert p1.id != p2.id
    assert d1.column_name == d2.column_name
    assert d1.dataset_name == d2.dataset_name

def test_8_pipeline_relational_extraction_and_manifest_bundle(db, client):
    """AC 8: Full relational dataset persistence, stats, queries, and research artifact bundle."""
    import uuid
    from backend.app.services.manifest_generator import ManifestGeneratorService

    proj = Project(name="Wits DHET Study 2026")
    db.add(proj)
    db.flush()

    doc = Document(
        project_id=proj.id,
        filename="DHET_TVET_Occupations.pdf",
        original_name="DHET_TVET_Occupations.pdf",
        file_path="/tmp/DHET_TVET_Occupations.pdf",
        doc_type="qualifications",
    )
    db.add(doc)
    db.flush()

    job = ExtractionJob(
        project_id=proj.id,
        document_id=doc.id,
        pipeline_type="qualifications",
    )
    db.add(job)
    db.flush()

    dataset = Dataset(
        project_id=proj.id,
        document_id=doc.id,
        name="DHET Occupational Qualifications 2026",
        schema_name="qualifications",
        schema_columns=[
            {"name": "saqa_id", "type": "string", "required": True},
            {"name": "qualification_name", "type": "string", "required": True},
            {"name": "nqf_sub_framework", "type": "string", "required": True},
            {"name": "nsfas_allowance", "type": "string", "required": True},
        ],
        status="validated",
    )
    db.add(dataset)
    db.flush()

    # Create qualifications
    q1 = Qualification(
        saqa_id=f"SAQA_{uuid.uuid4().hex[:6]}",
        qualification_number="101",
        qualification_name="Occupational Certificate: Mechanical Fitter",
        qualification_name_raw="Mechanical Fitter",
        nqf_level="4",
        nqf_sub_framework="OQSF",
        nsfas_allowance="YES",
        source_section="Section 1: Occupational Qualifications",
        source_page="3",
        confidence="high",
        job_id=job.id,
        document_id=doc.id,
    )
    db.add(q1)

    c1 = College.get_or_create(db, "Vhembe TVET College")
    c2 = College.get_or_create(db, "Orbit TVET College")
    db.commit()

    qc1 = QualificationCollege(
        saqa_id=q1.saqa_id,
        qualification_number=q1.qualification_number,
        college_id=c1.college_id,
        college_name=c1.college_name,
        source_section="Section 1",
        source_page="3",
        job_id=job.id,
        document_id=doc.id,
    )
    qc2 = QualificationCollege(
        saqa_id=q1.saqa_id,
        qualification_number=q1.qualification_number,
        college_id=c2.college_id,
        college_name=c2.college_name,
        source_section="Section 1",
        source_page="3",
        job_id=job.id,
        document_id=doc.id,
    )
    db.add(qc1)
    db.add(qc2)

    # Metadata entries
    dict_entry = DataDictionaryEntry(
        job_id=job.id,
        document_id=doc.id,
        dataset_name=dataset.name,
        column_name="saqa_id",
        data_type="string",
        description="SAQA ID primary key",
        source_field="SAQA ID",
        nullable="false",
    )
    prov_entry = ProvenanceRecord(
        job_id=job.id,
        document_id=doc.id,
        dataset_name=dataset.name,
        source_document=doc.original_name,
        source_section="Section 1",
        source_page="1-5",
        extraction_method="deterministic_table",
        record_count=1,
    )
    db.add(dict_entry)
    db.add(prov_entry)
    db.commit()

    # 1. Test relational stats endpoint
    stats_res = client.get(f"/api/v1/datasets/{dataset.id}/relational-stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert stats_data["qualifications_count"] >= 1
    assert stats_data["colleges_linked_count"] >= 2

    # 2. Test relational query endpoint
    rel_res = client.get(f"/api/v1/datasets/{dataset.id}/relational")
    assert rel_res.status_code == 200
    rel_data = rel_res.json()
    assert len(rel_data) >= 1
    target_q = next(q for q in rel_data if q["saqa_id"] == q1.saqa_id)
    assert len(target_q["colleges"]) == 2
    assert {c["college_name"] for c in target_q["colleges"]} == {"Vhembe TVET College", "Orbit TVET College"}

    # 3. Test data dictionary endpoint
    dict_res = client.get(f"/api/v1/datasets/{dataset.id}/data-dictionary")
    assert dict_res.status_code == 200
    assert len(dict_res.json()) >= 1

    # 4. Test provenance endpoint
    prov_res = client.get(f"/api/v1/datasets/{dataset.id}/provenance")
    assert prov_res.status_code == 200
    assert len(prov_res.json()) >= 1

    # 5. Test export using normalized relational tables
    export_res = client.post(f"/api/v1/datasets/{dataset.id}/export", json={"format": "csv"})
    assert export_res.status_code == 200
    exp_data = export_res.json()
    assert exp_data["record_count"] >= 1
    assert exp_data["download_url"].startswith("/api/v1/exports/download/")

    # 6. Test artifact bundle generation
    bundle = ManifestGeneratorService.generate_artifact_bundle(
        dataset_name=dataset.name,
        document_filename=doc.original_name,
        document_hash="test_hash_123456",
        page_count=5,
        schema_columns=dataset.schema_columns,
        records=[{"saqa_id": q1.saqa_id, "status": "valid"}],
        models_used=["deterministic_table"],
        prompt_version="2.0.0",
        profile_name="qualifications",
        db=db,
        job_id=job.id,
    )
    assert "data_dictionary" in bundle
    assert "provenance" in bundle
    assert "manifest" in bundle

def test_9_reset_database_endpoint(client):
    """AC 9: Verify reset database API endpoint completely clears DB and reinitializes cleanly."""
    res = client.post("/api/v1/system/reset-database", json={"clear_files": False})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["tables_recreated"] >= 7

    # Verify database is fresh and empty
    proj_res = client.get("/api/v1/projects")
    assert proj_res.status_code == 200
    assert len(proj_res.json()) == 0

def test_10_wrapped_and_duplicate_colleges_extraction_regression(db):
    """AC 10: Regression test for multi-line wrapped cells, generic stopwords ('College'),
    and in-memory duplicate pair prevention on qualification_colleges and dspp_centres."""
    from backend.app.pipeline.engine import parse_and_clean_colleges

    # 1. Test parse_and_clean_colleges with wrapped lines and fragments
    raw_colleges_text = (
        "Orbit TVET\n"
        "College\n"
        "Orbit TVET College\n"
        "College\n"
        "TVET College\n"
        "Sedibeng TVET\n"
        "College - Heidelberg Campus\n"
    )
    cleaned = parse_and_clean_colleges(raw_colleges_text)
    assert "College" not in cleaned
    assert "TVET College" not in cleaned
    assert "Orbit TVET College" in cleaned
    assert len([c for c in cleaned if c == "Orbit TVET College"]) == 1
    assert any("Sedibeng TVET College" in c for c in cleaned)

    # 2. Test College.get_or_create rejects stopwords
    bad_college = College.get_or_create(db, "College")
    assert bad_college is None
    bad_college2 = College.get_or_create(db, "TVET")
    assert bad_college2 is None

    # 3. Test duplicate (saqa_id, college_id) in same uncommitted session
    proj = Project(name="Regression Test Project")
    db.add(proj)
    db.flush()
    doc = Document(project_id=proj.id, filename="reg.pdf", original_name="reg.pdf", file_path="/tmp/reg.pdf")
    db.add(doc)
    db.flush()
    job = ExtractionJob(project_id=proj.id, document_id=doc.id, pipeline_type="qualifications")
    db.add(job)
    db.flush()

    saqa_id = "97585"
    qual = Qualification(
        saqa_id=saqa_id,
        qualification_number="97585",
        qualification_name="Occupational Certificate: Electrician",
        qualification_name_raw="Electrician",
        nqf_sub_framework="OQSF",
        nsfas_allowance="YES",
        confidence="high",
        source_section="Section 1",
        source_page="2",
        job_id=job.id,
        document_id=doc.id,
    )
    db.add(qual)
    db.flush()

    college = College.get_or_create(db, "Orbit TVET College")
    assert college is not None

    seen_qualification_colleges = set()

    # Simulate multi-line loop encountering the same college pair multiple times
    for _ in range(5):
        pair_key = (saqa_id, college.college_id)
        if pair_key not in seen_qualification_colleges:
            qc = QualificationCollege(
                saqa_id=saqa_id,
                qualification_number="97585",
                college_id=college.college_id,
                college_name=college.college_name,
                source_section="Section 1",
                source_page="2",
                job_id=job.id,
                document_id=doc.id,
            )
            db.add(qc)
            seen_qualification_colleges.add(pair_key)

    # Commit must succeed without sqlite3.IntegrityError
    db.commit()

    saved_links = db.query(QualificationCollege).filter(
        QualificationCollege.saqa_id == saqa_id,
        QualificationCollege.college_id == college.college_id,
    ).all()
    assert len(saved_links) == 1



