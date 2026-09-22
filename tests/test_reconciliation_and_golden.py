import os
import pytest
import pandas as pd
from pathlib import Path
from backend.app.services.reconciliation_engine import ReconciliationEngineService
from backend.app.services.evaluation_engine import EvaluationEngineService
from backend.app.services.manifest_generator import ManifestGeneratorService

def test_reconciliation_agreement_and_conflicts():
    records_a = [
        {"saqa_id": "118792", "qualification_name": "AI Developer", "nqf_level": 5, "source_page": 2},
        {"saqa_id": "998811", "qualification_name": "Data Engineer", "nqf_level": 6, "source_page": 3},
    ]
    # Model B agrees on first record, but has a different NQF level on the second record
    records_b = [
        {"saqa_id": "118792", "qualification_name": "AI Developer", "nqf_level": 5, "source_page": 2},
        {"saqa_id": "998811", "qualification_name": "Data Engineer", "nqf_level": 7, "source_page": 3},
    ]

    result = ReconciliationEngineService.reconcile(
        records_a=records_a,
        records_b=records_b,
        model_a_name="deepseek-reasoner",
        model_b_name="qwen2.5",
    )

    assert result.total_records_a == 2
    assert result.total_records_b == 2
    assert result.matched_records == 2
    # One field conflicted out of 6 fields evaluated
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.field_name == "nqf_level"
    assert conflict.value_a == 6
    assert conflict.value_b == 7
    assert conflict.resolution == "requires_review"

def test_evaluation_engine_benchmark():
    golden_df = pd.DataFrame([
        {"saqa_id": "1001", "title": "Electrician", "nqf": "4"},
        {"saqa_id": "1002", "title": "Plumber", "nqf": "4"},
        {"saqa_id": "1003", "title": "Welder", "nqf": "3"},
    ])

    actual_records = [
        {"saqa_id": "1001", "title": "Electrician", "nqf": "4"},
        {"saqa_id": "1002", "title": "Plumber", "nqf": "5"},  # nqf mismatch
        {"saqa_id": "1004", "title": "Mechanic", "nqf": "4"}, # extra record (1003 is missing)
    ]

    report = EvaluationEngineService.evaluate(
        dataset_id="test-ds-1",
        golden_df=golden_df,
        actual_records=actual_records,
        golden_name="Artisans Ground Truth",
    )

    assert report.total_expected_records == 3
    assert report.total_actual_records == 3
    assert report.matched_records_count == 2
    assert report.missing_records_count == 1
    assert report.extra_records_count == 1
    assert report.record_recall == pytest.approx(66.67, rel=1e-2)
    assert report.record_precision == pytest.approx(66.67, rel=1e-2)
    assert report.field_mismatches_count == 1

def test_manifest_bundle_generation(tmp_path):
    schema_cols = [
        {"name": "saqa_id", "original_name": "SAQA ID", "type": "string", "identifier": True},
        {"name": "title", "original_name": "Qualification Title", "type": "string", "identifier": False},
    ]
    records = [
        {"saqa_id": "118792", "title": "AI Developer", "source_page": 4, "status": "valid"},
    ]

    bundle = ManifestGeneratorService.generate_artifact_bundle(
        dataset_name="Test Qualifications",
        document_filename="qualifications.pdf",
        document_hash="abc123hash",
        page_count=10,
        schema_columns=schema_cols,
        records=records,
        models_used=["deepseek-reasoner"],
        prompt_version="2.0.0",
        profile_name="qualifications",
        output_dir=tmp_path,
    )

    assert "data_dictionary" in bundle
    assert "provenance" in bundle
    assert "manifest" in bundle
    assert os.path.exists(bundle["data_dictionary"])
    assert os.path.exists(bundle["provenance"])
    assert os.path.exists(bundle["manifest"])
