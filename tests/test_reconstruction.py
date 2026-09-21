import pytest
from extractors.base import RawTable
from core.reconstructor import TableReconstructor


def test_table_continuation_and_header_deduplication():
    recon = TableReconstructor()

    # Table on Page 1
    t1 = RawTable(
        page_number=1,
        table_index=0,
        headers=["SAQA ID", "Qualification", "NQF"],
        rows=[
            ["118792", "AI Developer", "5"],
            ["118793", "Cloud Engineer", "6"],
        ],
        extraction_method="test",
    )

    # Continuation Table on Page 2 with repeated header in rows[0]
    t2 = RawTable(
        page_number=2,
        table_index=0,
        headers=["SAQA ID", "Qualification", "NQF"],
        rows=[
            ["SAQA ID", "Qualification", "NQF"],  # Repeated header
            ["102145", "Solar Technician", "5"],
        ],
        extraction_method="test",
    )

    reconstructed = recon.reconstruct([t1, t2])
    assert len(reconstructed) == 1
    master = reconstructed[0]
    assert master.row_count == 3  # Repeated header stripped
    assert master.rows[2][0] == "102145"


def test_wrapped_row_healing():
    recon = TableReconstructor()

    t1 = RawTable(
        page_number=1,
        table_index=0,
        headers=["SAQA ID", "Title", "NQF"],
        rows=[
            ["118792", "Occupational Certificate: Artificial", "5"],
            ["", "Intelligence Software Developer", ""],  # Continuation line
        ],
        extraction_method="test",
    )

    reconstructed = recon.reconstruct([t1])
    assert len(reconstructed) == 1
    master = reconstructed[0]
    assert master.row_count == 1
    assert "Artificial Intelligence Software Developer" in master.rows[0][1]
