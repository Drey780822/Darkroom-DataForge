import pytest
from core.normalizer import Normalizer
from models.record import Record
from models.provenance import ProvenanceRecord, RecordStatus


def test_whitespace_and_unicode_normalization():
    raw_text = "  Occupational\u00a0Certificate:\t“AI Software”–Dev \n\n "
    normalized, is_mod = Normalizer.normalize_value(raw_text)
    assert normalized == 'Occupational Certificate: "AI Software"-Dev'
    assert is_mod is True


def test_null_token_detection():
    for null_tok in ["N/A", "na", "-", "--", "None", "null", ""]:
        val, is_mod = Normalizer.normalize_value(null_tok)
        assert val is None


def test_leading_zero_preservation():
    # OFO code with leading zero should preserve leading zero
    val, _ = Normalizer.normalize_value("012345", field_name="ofo_code")
    assert val == "012345"

    # Numeric value that is not code should convert to int
    val2, _ = Normalizer.normalize_value("42", field_name="count")
    assert val2 == 42


def test_deduplicate_records():
    prov = ProvenanceRecord(
        source_document="test.pdf",
        source_page=1,
        extraction_method="test",
    )

    r1 = Record(provenance=prov)
    r1.set_value("saqa_id", "118792", "118792")
    r1.set_value("title", "AI Dev", "AI Dev")

    r2 = Record(provenance=prov)
    r2.set_value("saqa_id", "118792", "118792")
    r2.set_value("title", "AI Dev", "AI Dev")

    r3 = Record(provenance=prov)
    r3.set_value("saqa_id", "102145", "102145")
    r3.set_value("title", "Solar Tech", "Solar Tech")

    unique, dup_count = Normalizer.deduplicate_records([r1, r2, r3], key_fields=["saqa_id"])
    assert len(unique) == 2
    assert dup_count == 1
