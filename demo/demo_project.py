from __future__ import annotations
from pathlib import Path
from core.project import Project
from core.pipeline import DataforgePipeline
from .sample_generator import SampleGenerator


class DemoProjectManager:
    """Manages synthetic demo projects and fixture generation for onboarding and tests."""

    @classmethod
    def setup_demo_project(cls, base_dir: str = "./dataforge_projects/TVET_Qualifications_Demo") -> Project:
        proj_dir = Path(base_dir).resolve()
        proj_dir.mkdir(parents=True, exist_ok=True)

        # Generate sample files inside a samples folder
        samples_dir = proj_dir / "sample_fixtures"
        samples_dir.mkdir(exist_ok=True)

        tvet_pdf = samples_dir / "DHET_TVET_Qualifications_2026.pdf"
        qlfs_pdf = samples_dir / "StatsSA_QLFS_Codebook_2026.pdf"
        oihd_pdf = samples_dir / "DHET_OIHD_National_Report_2024.pdf"

        SampleGenerator.generate_tvet_qualifications_pdf(str(tvet_pdf))
        SampleGenerator.generate_qlfs_codebook_pdf(str(qlfs_pdf))
        SampleGenerator.generate_oihd_report_pdf(str(oihd_pdf))

        # Create project and add TVET qualifications PDF
        project = Project(
            workspace_path=str(proj_dir),
            name="TVET Qualifications Demo",
            description="Demonstration project showing TVET Occupational Qualifications 1:N normalization into qualifications.csv and qualification_colleges.csv."
        )

        project.add_document(str(tvet_pdf))
        project.add_document(str(qlfs_pdf))
        project.add_document(str(oihd_pdf))

        return project

    @classmethod
    def run_full_demo(cls, base_dir: str = "./dataforge_projects/TVET_Qualifications_Demo"):
        """Creates and executes the complete pipeline on the demo project."""
        project = cls.setup_demo_project(base_dir)
        pipeline = DataforgePipeline(project)
        result = pipeline.run_pipeline()
        return project, result
