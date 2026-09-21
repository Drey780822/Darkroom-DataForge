import pytest
from core.validator import Validator
from models.dataset import Dataset, DatasetMetadata
from models.field import FieldDefinition, DataType
from models.record import Record
from models.provenance import ProvenanceRecord
from models.validation import ValidationRule, IssueSeverity


def test_validator_required_and_range():
    cols = [
        FieldDefinition(name="saqa_id", display_name="SAQA ID", data_type=DataType.STRING, required=True, is_primary_key=True),
        FieldDefinition(name="qualification", display_name="Qualification", data_type=DataType.STRING, required=True),
        FieldDefinition(name="nqf_level", display_name="NQF Level", data_type=DataType.INTEGER, required=True),
    ]

    prov = ProvenanceRecord(source_document="doc.pdf", source_page=1, extraction_method="test")

    # Record 1: Valid
    r1 = Record(provenance=prov)
    r1.set_value("saqa_id", "118792", "118792")
    r1.set_value("qualification", "AI Developer", "AI Developer")
    r1.set_value("nqf_level", 5, 5)

    # Record 2: Missing SAQA ID
    r2 = Record(provenance=prov)
    r2.set_value("saqa_id", "", None)
    r2.set_value("qualification", "Cloud Engineer", "Cloud Engineer")
    r2.set_value("nqf_level", 6, 6)

    # Record 3: Invalid NQF (15 > 10)
    r3 = Record(provenance=prov)
    r3.set_value("saqa_id", "118793", "118793")
    r3.set_value("qualification", "Security Analyst", "Security Analyst")
    r3.set_value("nqf_level", 15, 15)

    ds = Dataset(
        metadata=DatasetMetadata(name="test_dataset", display_name="Test Dataset"),
        columns=cols,
        records=[r1, r2, r3],
        primary_key=["saqa_id"],
    )

    val = Validator()
    summary = val.validate_dataset(ds)

    assert summary.critical_count >= 2
    assert summary.records_with_issues >= 2
    assert any("Missing required value" in i.message for i in summary.issues)
    assert any("outside valid range" in i.message for i in summary.issues)
