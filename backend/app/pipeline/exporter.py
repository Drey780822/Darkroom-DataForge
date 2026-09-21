import io
import json
from typing import List, Dict, Any, Optional
import pandas as pd

class DatasetExporter:
    """Exports datasets to various formats (CSV, JSON, XLSX) with optional provenance columns."""

    @classmethod
    def export(
        cls,
        records: List[Dict[str, Any]],
        format: str = "csv",
        include_provenance: bool = True,
        selected_columns: Optional[List[str]] = None,
    ) -> bytes:
        flat_records = []
        for r in records:
            row_data = dict(r.get("data", {}))
            if include_provenance:
                prov = r.get("provenance", {})
                row_data["_prov_doc"] = prov.get("document_name", "")
                row_data["_prov_page"] = prov.get("page_number", "")
                row_data["_prov_confidence"] = r.get("confidence_score", 1.0)
                row_data["_prov_status"] = r.get("status", "valid")
            
            if selected_columns:
                row_data = {k: v for k, v in row_data.items() if k in selected_columns or k.startswith("_prov_")}

            flat_records.append(row_data)

        df = pd.DataFrame(flat_records)

        fmt = format.lower().strip()
        if fmt == "csv":
            return df.to_csv(index=False).encode("utf-8")
        elif fmt == "json":
            return df.to_json(orient="records", indent=2).encode("utf-8")
        elif fmt in ["xlsx", "excel"]:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="DataForge_Dataset")
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")
