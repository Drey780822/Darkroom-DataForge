from __future__ import annotations
import re
import unicodedata
from typing import Any, Tuple, List, Set, Dict, Optional
from models.record import Record, CellValue
from models.provenance import ProvenanceRecord, RecordStatus


class Normalizer:
    """Standardizes string values, whitespace, unicode, identifiers, and null tokens while preserving raw provenance."""

    NULL_TOKENS = {
        "", "n/a", "na", "null", "none", "-", "--", "nil", "unknown", "undefined", "#n/a", "nan"
    }

    LIGATURES = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "œ": "oe",
        "æ": "ae",
    }

    SA_PROVINCES = {
        "gp": "Gauteng",
        "gau": "Gauteng",
        "gauteng": "Gauteng",
        "kzn": "KwaZulu-Natal",
        "kwazulu-natal": "KwaZulu-Natal",
        "wc": "Western Cape",
        "western cape": "Western Cape",
        "ec": "Eastern Cape",
        "eastern cape": "Eastern Cape",
        "fs": "Free State",
        "free state": "Free State",
        "mp": "Mpumalanga",
        "mpu": "Mpumalanga",
        "mpumalanga": "Mpumalanga",
        "lp": "Limpopo",
        "lim": "Limpopo",
        "limpopo": "Limpopo",
        "nw": "North West",
        "north west": "North West",
        "nc": "Northern Cape",
        "northern cape": "Northern Cape",
        "national": "National",
    }

    @classmethod
    def clean_unicode(cls, text: str) -> str:
        if not text:
            return ""
        # Remove zero-width spaces, soft hyphens, and BOM
        for zw in ["\u200b", "\u200c", "\u200d", "\ufeff", "\u00ad"]:
            text = text.replace(zw, "")
        # Expand ligatures
        for lig, repl in cls.LIGATURES.items():
            text = text.replace(lig, repl)
        # Normalize Unicode to NFKC
        text = unicodedata.normalize("NFKC", text)
        # Replace non-breaking spaces and smart quotes/dashes
        text = text.replace("\u00a0", " ")
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("‘", "'").replace("’", "'")
        text = text.replace("–", "-").replace("—", "-")
        return text

    @classmethod
    def normalize_value(cls, raw: Any, field_name: str = "") -> Tuple[Any, bool]:
        if raw is None:
            return None, False

        val_str = str(raw)
        cleaned = cls.clean_unicode(val_str)
        cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Check for null representations
        if cleaned.lower() in cls.NULL_TOKENS:
            return None, (raw is not None and str(raw).strip() != "")

        # Preserve leading zeros for specific ID / code columns (e.g. saqa_id, ofo_code, postal_code)
        is_code_field = any(term in field_name.lower() for term in ["id", "code", "ofo", "saqa"])
        if is_code_field and re.match(r"^0\d+$", cleaned):
            return cleaned, (cleaned != str(raw))

        # Check if integer
        if re.match(r"^-?\d+$", cleaned) and not is_code_field:
            try:
                num = int(cleaned)
                return num, (str(raw) != cleaned)
            except ValueError:
                pass

        # Check if float
        if re.match(r"^-?\d+\.\d+$", cleaned) and not is_code_field:
            try:
                num = float(cleaned)
                return num, (str(raw) != cleaned)
            except ValueError:
                pass

        # Check boolean
        if cleaned.lower() in ["true", "yes", "y"]:
            return True, (raw is not True and str(raw) != "True")
        if cleaned.lower() in ["false", "no", "n"]:
            return False, (raw is not False and str(raw) != "False")

        # Standardize South African province if province-related field
        is_prov_field = any(term in field_name.lower() for term in ["province", "prov", "region"])
        if is_prov_field and cleaned.lower() in cls.SA_PROVINCES:
            std_prov = cls.SA_PROVINCES[cleaned.lower()]
            return std_prov, (std_prov != str(raw))

        is_modified = (cleaned != str(raw))
        return cleaned, is_modified

    @classmethod
    def normalize_record(cls, record: Record) -> Record:
        """Applies normalization across all cells in a record, tracking both raw and normalized values."""
        for field_name, cell in record.cells.items():
            norm_val, modified = cls.normalize_value(cell.raw_value, field_name=field_name)
            cell.normalized_value = norm_val
            cell.is_modified = modified

        record.provenance.status = RecordStatus.NORMALIZED
        return record

    @classmethod
    def deduplicate_records(cls, records: List[Record], key_fields: Optional[List[str]] = None) -> Tuple[List[Record], int]:
        """Detects and removes duplicate records based on normalized values of key fields."""
        unique_records: List[Record] = []
        seen_signatures: Set[str] = set()
        duplicate_count = 0

        for r in records:
            if key_fields:
                sig_parts = [str(r.get_value(k, prefer_normalized=True)) for k in key_fields]
            else:
                sig_parts = [str(r.get_value(k, prefer_normalized=True)) for k in sorted(r.cells.keys())]

            signature = "||".join(sig_parts)
            if signature in seen_signatures:
                duplicate_count += 1
            else:
                seen_signatures.add(signature)
                unique_records.append(r)

        return unique_records, duplicate_count
