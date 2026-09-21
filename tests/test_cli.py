import pytest
from pathlib import Path
from demo.sample_generator import SampleGenerator
from cli.main import main


@pytest.fixture(scope="session")
def cli_sample_pdf(tmp_path_factory):
    d = tmp_path_factory.mktemp("cli_test")
    pdf = d / "sample.pdf"
    SampleGenerator.generate_tvet_qualifications_pdf(str(pdf))
    return str(pdf)


def test_cli_inspect(cli_sample_pdf):
    rc = main(["inspect", cli_sample_pdf])
    assert rc == 0


def test_cli_process_and_export(tmp_path, cli_sample_pdf):
    proj_dir = tmp_path / "cli_project"
    rc = main(["process", cli_sample_pdf, "--project", str(proj_dir), "--format", "csv"])
    assert rc == 0
    assert (proj_dir / "project.json").exists()
    assert (proj_dir / "manifest.json").exists()
    assert (proj_dir / "exports" / "qualifications.csv").exists()


def test_cli_validate(tmp_path, cli_sample_pdf):
    proj_dir = tmp_path / "cli_val_proj"
    main(["process", cli_sample_pdf, "--project", str(proj_dir)])
    rc = main(["validate", str(proj_dir)])
    assert rc == 0
