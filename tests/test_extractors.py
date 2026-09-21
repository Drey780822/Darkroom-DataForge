import pytest
from demo.sample_generator import SampleGenerator
from extractors import (
    QualificationsExtractor,
    CodebookExtractor,
    OccupationsExtractor,
    PdfTablesExtractor,
)


@pytest.fixture(scope="session")
def pdf_fixtures(tmp_path_factory):
    d = tmp_path_factory.mktemp("extractor_fixtures")
    tvet = str(d / "tvet.pdf")
    qlfs = str(d / "qlfs.pdf")
    oihd = str(d / "oihd.pdf")

    SampleGenerator.generate_tvet_qualifications_pdf(tvet)
    SampleGenerator.generate_qlfs_codebook_pdf(qlfs)
    SampleGenerator.generate_oihd_report_pdf(oihd)

    return {"tvet": tvet, "qlfs": qlfs, "oihd": oihd}


def test_qualifications_extractor(pdf_fixtures):
    ext = QualificationsExtractor()
    res = ext.extract(pdf_fixtures["tvet"])
    assert res.total_rows >= 10
    first_table = res.tables[0]
    assert "saqa_id" in first_table.headers
    # Check that SAQA ID 118792 is present
    ids = [r[0] for r in first_table.rows]
    assert "118792" in ids


def test_codebook_extractor(pdf_fixtures):
    ext = CodebookExtractor()
    res = ext.extract(pdf_fixtures["qlfs"])
    assert res.total_rows >= 10
    vars_extracted = [r[0] for r in res.tables[0].rows]
    assert "Q13GENDER" in vars_extracted
    assert "Q21PROVINCE" in vars_extracted


def test_occupations_extractor(pdf_fixtures):
    ext = OccupationsExtractor()
    res = ext.extract(pdf_fixtures["oihd"])
    assert res.total_rows >= 5
    ofo_codes = [r[0] for r in res.tables[0].rows]
    assert "251201" in ofo_codes  # Software Developer
