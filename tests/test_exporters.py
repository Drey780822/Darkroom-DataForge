import pytest
from pathlib import Path
from exporters import CsvExporter, JsonExporter, ExcelExporter, SqlExporter
from models.dataset import Dataset, DatasetMetadata
from models.field import FieldDefinition, DataType
from models.record import Record
from models.provenance import ProvenanceRecord


@pytest.fixture
def sample_dataset():
    cols = [
        FieldDefinition(name="saqa_id", display_name="SAQA ID", data_type=DataType.STRING, required=True, is_primary_key=True),
        FieldDefinition(name="title", display_name="Title", data_type=DataType.STRING, required=True),
    ]
    prov = ProvenanceRecord(source_document="doc.pdf", source_page=1, extraction_method="test")
    r1 = Record(provenance=prov)
    r1.set_value("saqa_id", "118792", "118792")
    r1.set_value("title", "AI Developer", "AI Developer")

    return Dataset(
        metadata=DatasetMetadata(name="test_qual", display_name="Test Qual"),
        columns=cols,
        records=[r1],
        primary_key=["saqa_id"],
    )


def test_csv_exporter(tmp_path, sample_dataset):
    out = tmp_path / "test.csv"
    CsvExporter().export_dataset(sample_dataset, str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "saqa_id,title" in content
    assert "118792,AI Developer" in content


def test_json_exporter(tmp_path, sample_dataset):
    out = tmp_path / "test.json"
    JsonExporter().export_dataset(sample_dataset, str(out))
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "118792" in content


def test_excel_exporter(tmp_path, sample_dataset):
    out_dir = tmp_path / "excel_out"
    ExcelExporter().export_all([sample_dataset], str(out_dir))
    xlsx = out_dir / "extracted_datasets.xlsx"
    assert xlsx.exists()
    assert xlsx.stat().st_size > 1000


def test_excel_exporter_empty_datasets(tmp_path):
    out_dir = tmp_path / "excel_empty_out"
    ExcelExporter().export_all([], str(out_dir))
    xlsx = out_dir / "extracted_datasets.xlsx"
    assert xlsx.exists()


def test_sql_exporter(sample_dataset):
    sql = SqlExporter().generate_ddl([sample_dataset])
    assert 'CREATE TABLE IF NOT EXISTS "test_qual"' in sql
    assert '"saqa_id" TEXT' in sql
    assert 'CONSTRAINT "pk_test_qual" PRIMARY KEY ("saqa_id")' in sql
    assert 'INSERT INTO "test_qual"' in sql


def test_sql_exporter_reserved_keywords():
    cols = [
        FieldDefinition(name="order", display_name="Order", data_type=DataType.INTEGER, required=True, is_primary_key=True),
        FieldDefinition(name="value", display_name="Value", data_type=DataType.STRING),
        FieldDefinition(name="desc", display_name="Description", data_type=DataType.STRING),
        FieldDefinition(name="group", display_name="Group", data_type=DataType.STRING),
    ]
    prov = ProvenanceRecord(source_document="doc.pdf", source_page=1, extraction_method="test")
    r1 = Record(provenance=prov)
    r1.set_value("order", 1, 1)
    r1.set_value("value", "A", "A")
    r1.set_value("desc", "Description text", "Description text")
    r1.set_value("group", "Grp1", "Grp1")

    ds = Dataset(
        metadata=DatasetMetadata(name="reserved_table", display_name="Reserved Table"),
        columns=cols,
        records=[r1],
        primary_key=["order"],
    )

    sql = SqlExporter().generate_ddl([ds])
    assert 'CREATE TABLE IF NOT EXISTS "reserved_table"' in sql
    assert '"order" INTEGER NOT NULL' in sql
    assert '"value" TEXT NULL' in sql
    assert '"desc" TEXT NULL' in sql
    assert '"group" TEXT NULL' in sql
    assert 'INSERT INTO "reserved_table" ("order", "value", "desc", "group")' in sql

