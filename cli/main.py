from __future__ import annotations
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path when invoked directly
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.inspector import DocumentInspector
from core.classifier import DocumentClassifier
from core.project import Project
from core.pipeline import DataforgePipeline
from exporters import CsvExporter, JsonExporter, ExcelExporter, SqlExporter


def cmd_inspect(args):
    path = Path(args.file).resolve()
    if not path.exists():
        print(f"Error: File {args.file} not found.", file=sys.stderr)
        return 1

    inspector = DocumentInspector()
    classifier = DocumentClassifier()
    meta = inspector.create_document_metadata(str(path))
    classification = classifier.classify(meta)

    print("==================================================")
    print("DARKROOM DATAFORGE - DOCUMENT INSPECTION")
    print("==================================================")
    print(f"File:                   {meta.filename}")
    print(f"Size:                   {meta.file_size_bytes:,} bytes")
    print(f"SHA-256:                {meta.sha256_hash[:16]}...")
    print(f"Pages:                  {meta.inspection.page_count}")
    print(f"Digital Text:           {'Yes' if meta.inspection.has_digital_text else 'No'}")
    print(f"Total Text Length:      {meta.inspection.total_text_length:,} characters")
    print(f"Table Likelihood:       {meta.inspection.table_likelihood_score*100:.0f}%")
    print(f"Scanned Page Ratio:     {meta.inspection.scanned_pages_ratio*100:.0f}%")
    print("--------------------------------------------------")
    print(f"Classified Type:        {classification.document_type.label}")
    print(f"Confidence:             {classification.confidence*100:.0f}%")
    print(f"Recommended Extractor:  {classification.recommended_extractor}")
    print("Reasons:")
    for r in classification.reasons:
        print(f"  * {r}")
    print("==================================================")
    return 0


def cmd_process(args):
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: Input path {args.input} does not exist.", file=sys.stderr)
        return 1

    project_dir = Path(args.project or "./dataforge_workspace").resolve()
    project = Project(workspace_path=str(project_dir), name=project_dir.name)

    pdf_files = []
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        pdf_files.append(input_path)
    elif input_path.is_dir():
        pdf_files = sorted(list(input_path.glob("*.pdf")) + list(input_path.glob("*.PDF")))

    if not pdf_files:
        print(f"Error: No PDF files found in {args.input}", file=sys.stderr)
        return 1

    print(f"Importing {len(pdf_files)} PDF(s) into project '{project.metadata.name}'...")
    for pdf in pdf_files:
        doc_meta = project.add_document(str(pdf))
        print(f"  + Added {doc_meta.filename}")

    pipeline = DataforgePipeline(project)
    print("Executing extraction pipeline...")
    result = pipeline.run_pipeline()

    print("\nExtraction Summary:")
    print(f"  Run ID:           {result.run_id}")
    print(f"  Status:           {result.overall_status.value}")
    print(f"  Records:          {result.manifest.total_records_extracted}")
    print(f"  Datasets:         {', '.join([d.metadata.name for d in result.datasets])}")
    print(f"  Audit Manifest:   {project.workspace.root_path / 'manifest.json'}")

    # Auto-export if requested
    if args.format:
        export_dir = project.workspace.exports_dir
        if args.format == "csv" or args.format == "all":
            CsvExporter().export_all(result.datasets, str(export_dir))
        if args.format == "json" or args.format == "all":
            JsonExporter().export_all(result.datasets, str(export_dir))
        if args.format == "excel" or args.format == "all":
            ExcelExporter().export_all(result.datasets, str(export_dir))
        if args.format == "sql" or args.format == "all":
            SqlExporter().export_all(result.datasets, str(export_dir))
        print(f"Exported {args.format.upper()} files to: {export_dir}")

    return 0


def cmd_validate(args):
    project_dir = Path(args.project).resolve()
    if not project_dir.exists():
        print(f"Error: Project workspace {args.project} not found.", file=sys.stderr)
        return 1

    project = Project(workspace_path=str(project_dir))
    if not project.datasets:
        print("No extracted datasets in project to validate.", file=sys.stderr)
        return 1

    from core.validator import Validator
    validator = Validator()
    print(f"Validating {len(project.datasets)} dataset(s) in '{project.metadata.name}'...")
    
    total_crit = 0
    total_warn = 0

    for name, ds in project.datasets.items():
        summary = validator.validate_dataset(ds)
        total_crit += summary.critical_count
        total_warn += summary.warning_count
        print(f"  Dataset: {name}")
        print(f"    Records: {ds.record_count}")
        print(f"    Critical Issues: {summary.critical_count}")
        print(f"    Warnings:        {summary.warning_count}")

    print("--------------------------------------------------")
    print(f"Total: {total_crit} Critical, {total_warn} Warnings")
    return 0 if total_crit == 0 else 2


def cmd_export(args):
    project_dir = Path(args.project).resolve()
    if not project_dir.exists():
        print(f"Error: Project workspace {args.project} not found.", file=sys.stderr)
        return 1

    project = Project(workspace_path=str(project_dir))
    datasets = list(project.datasets.values())
    if not datasets:
        print("No datasets available to export.", file=sys.stderr)
        return 1

    out_dir = Path(args.output or project.workspace.exports_dir).resolve()
    fmt = (args.format or "csv").lower()

    if fmt == "csv":
        paths = CsvExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
    elif fmt == "json":
        paths = JsonExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
    elif fmt == "excel":
        paths = ExcelExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
    elif fmt == "sql":
        paths = SqlExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
    elif fmt == "all":
        paths = []
        paths += CsvExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
        paths += JsonExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
        paths += ExcelExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
        paths += SqlExporter().export_all(datasets, str(out_dir), include_provenance=args.provenance)
    else:
        print(f"Unsupported format: {fmt}", file=sys.stderr)
        return 1

    print(f"Exported {len(datasets)} dataset(s) ({fmt.upper()}) to {out_dir}:")
    for p in paths:
        print(f"  -> {Path(p).name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataforge",
        description="Darkroom DataForge: Document Intelligence & Structured Dataset Generation CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect and classify a PDF document")
    p_inspect.add_argument("file", help="Path to PDF document")

    # process
    p_process = subparsers.add_parser("process", help="Process PDF documents into structured datasets")
    p_process.add_argument("input", help="Path to PDF file or directory of PDFs")
    p_process.add_argument("--project", "-p", help="Target project workspace directory")
    p_process.add_argument("--format", "-f", choices=["csv", "json", "excel", "sql", "all"], default="csv", help="Auto export format")

    # validate
    p_validate = subparsers.add_parser("validate", help="Validate extracted datasets in a project workspace")
    p_validate.add_argument("project", help="Path to project workspace directory")

    # export
    p_export = subparsers.add_parser("export", help="Export datasets to CSV, JSON, Excel, or PostgreSQL SQL")
    p_export.add_argument("project", help="Path to project workspace directory")
    p_export.add_argument("--format", "-f", choices=["csv", "json", "excel", "sql", "all"], default="csv")
    p_export.add_argument("--output", "-o", help="Custom output directory")
    p_export.add_argument("--provenance", action="store_true", help="Include provenance metadata columns")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "inspect":
        return cmd_inspect(args)
    elif args.command == "process":
        return cmd_process(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "export":
        return cmd_export(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
