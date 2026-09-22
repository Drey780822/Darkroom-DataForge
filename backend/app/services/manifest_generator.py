import os
import json
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.app.config import settings

class ManifestGeneratorService:
    """Generates complete research audit artifacts: data_dictionary.csv, provenance.csv, and extraction_manifest.json."""

    @classmethod
    def generate_artifact_bundle(
        cls,
        dataset_name: str,
        document_filename: str,
        document_hash: str,
        page_count: int,
        schema_columns: List[Dict[str, Any]],
        records: List[Dict[str, Any]],
        models_used: List[str],
        prompt_version: str,
        profile_name: str,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, str]:
        base_dir = output_dir or (settings.exports_path / f"bundle_{dataset_name.replace(' ', '_')}_{int(datetime.now().timestamp())}")
        base_dir.mkdir(parents=True, exist_ok=True)
        meta_dir = base_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)

        generated_files = {}

        # 1. data_dictionary.csv
        dict_path = meta_dir / "data_dictionary.csv"
        dict_fields = [
            "dataset_name",
            "column_name",
            "source_label",
            "data_type",
            "nullable",
            "description",
            "identifier",
            "example_value",
            "source_pages",
        ]
        with open(dict_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=dict_fields)
            writer.writeheader()
            for col in schema_columns:
                col_name = col.get("name", "")
                ex_val = ""
                sample_pages = set()
                for r in records[:50]:
                    if col_name in r and r[col_name]:
                        ex_val = str(r[col_name])
                        break
                for r in records:
                    p = r.get("source_page") or r.get("provenance", {}).get("page_number")
                    if p:
                        sample_pages.add(str(p))

                writer.writerow({
                    "dataset_name": dataset_name,
                    "column_name": col_name,
                    "source_label": col.get("original_name") or col.get("source_label") or col_name,
                    "data_type": col.get("type", "string"),
                    "nullable": "YES" if not col.get("required") else "NO",
                    "description": col.get("description", f"Extracted column {col_name}"),
                    "identifier": "YES" if col.get("identifier") or col_name in ["saqa_id", "ofo_code"] else "NO",
                    "example_value": ex_val,
                    "source_pages": ", ".join(sorted(list(sample_pages), key=lambda x: int(x) if x.isdigit() else 0)[:10]),
                })
        generated_files["data_dictionary"] = str(dict_path)

        # 2. provenance.csv
        prov_path = meta_dir / "provenance.csv"
        prov_fields = ["row_index", "document_filename", "page_number", "method", "model", "confidence"]
        with open(prov_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=prov_fields)
            writer.writeheader()
            for idx, r in enumerate(records):
                prov = r.get("provenance") or {}
                writer.writerow({
                    "row_index": idx + 1,
                    "document_filename": prov.get("document_name", document_filename),
                    "page_number": prov.get("page_number", r.get("source_page", 1)),
                    "method": prov.get("method", "llm_structured_extraction"),
                    "model": prov.get("model", ", ".join(models_used)),
                    "confidence": r.get("confidence_score", r.get("confidence", 1.0)),
                })
        generated_files["provenance"] = str(prov_path)

        # 3. extraction_manifest.json
        manifest_path = meta_dir / "extraction_manifest.json"
        total_recs = len(records)
        verified_count = sum(1 for r in records if r.get("status") in ["valid", "human_reviewed"])
        review_required_count = sum(1 for r in records if r.get("status") in ["warning", "error"] or r.get("issues"))

        manifest_data = {
            "document": document_filename,
            "document_hash": document_hash,
            "pages": page_count,
            "datasets": [dataset_name],
            "records_extracted": total_recs,
            "records_verified": verified_count,
            "records_review_required": review_required_count,
            "models": models_used,
            "extraction_profile": profile_name,
            "prompt_version": prompt_version,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        generated_files["manifest"] = str(manifest_path)

        return generated_files
