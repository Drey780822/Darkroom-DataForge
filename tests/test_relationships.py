import pytest
from core.relationship_detector import RelationshipDetector
from models.dataset import Dataset, DatasetMetadata
from models.field import FieldDefinition, DataType
from models.record import Record
from models.provenance import ProvenanceRecord


def test_one_to_many_decomposition():
    cols = [
        FieldDefinition(name="saqa_id", display_name="SAQA ID", data_type=DataType.STRING, required=True, is_primary_key=True),
        FieldDefinition(name="qualification", display_name="Qualification", data_type=DataType.STRING, required=True),
        FieldDefinition(name="participating_colleges", display_name="Colleges", data_type=DataType.LIST, required=False),
    ]

    prov = ProvenanceRecord(source_document="doc.pdf", source_page=1, extraction_method="test")

    r1 = Record(provenance=prov)
    r1.set_value("saqa_id", "118792", "118792")
    r1.set_value("qualification", "AI Developer", "AI Developer")
    r1.set_value("participating_colleges", "Motheo TVET; Umfolozi TVET", "Motheo TVET; Umfolozi TVET")

    ds = Dataset(
        metadata=DatasetMetadata(name="qualifications", display_name="Qualifications"),
        columns=cols,
        records=[r1],
        primary_key=["saqa_id"],
    )

    detected_col = RelationshipDetector.detect_list_column(ds)
    assert detected_col is not None
    assert detected_col.name == "participating_colleges"

    parent, child, rel = RelationshipDetector.decompose_one_to_many(
        parent_dataset=ds,
        list_column_name="participating_colleges",
        child_dataset_name="qualification_colleges",
        child_item_column_name="college_name",
        parent_pk_column="saqa_id",
    )

    assert "participating_colleges" not in parent.column_names
    assert parent.record_count == 1
    assert child.record_count == 2
    assert child.column_names == ["saqa_id", "college_name"]
    assert rel.parent_dataset == "qualifications"
    assert rel.child_dataset == "qualification_colleges"
