from __future__ import annotations
import re
from typing import List, Optional
from difflib import SequenceMatcher
from extractors.base import RawTable


class TableReconstructor:
    """Reconstructs, joins, and heals fragmented or multi-page PDF tables."""

    @staticmethod
    def header_similarity(headers1: List[str], headers2: List[str]) -> float:
        if not headers1 or not headers2:
            return 0.0
        h1 = " ".join([h.lower().strip() for h in headers1])
        h2 = " ".join([h.lower().strip() for h in headers2])
        return SequenceMatcher(None, h1, h2).ratio()

    @staticmethod
    def is_noise_row(row: List[str]) -> bool:
        combined = " ".join(row).lower().strip()
        if not combined:
            return True
        # Page numbers, footers, source citations
        if re.search(r"^(page\s+\d+(\s+of\s+\d+)?|\d+\s*/\s*\d+)$", combined):
            return True
        if re.search(r"^(source\s*:|note\s*:|continued\s+on\s+next\s+page)", combined):
            return True
        return False

    @classmethod
    def heal_rows(cls, raw_rows: List[List[str]], col_count: int) -> List[List[str]]:
        """Heals wrapped / orphaned lines where primary key column is blank and subsequent cols contain continuation text."""
        healed: List[List[str]] = []

        for r in raw_rows:
            if cls.is_noise_row(r):
                continue

            # Check if this row is a wrapped continuation of the previous row:
            # First column is empty, but column 1 or later has content
            is_continuation = bool(healed and len(r) > 1 and not r[0].strip() and any(r[1:]))

            if is_continuation:
                prev = healed[-1]
                for c_idx in range(1, min(len(r), len(prev))):
                    if r[c_idx].strip():
                        prev[c_idx] = f"{prev[c_idx]} {r[c_idx]}".strip()
            else:
                # Pad or slice to expected column count
                row_copy = list(r)
                if len(row_copy) < col_count:
                    row_copy += [""] * (col_count - len(row_copy))
                elif len(row_copy) > col_count:
                    row_copy = row_copy[:col_count]
                healed.append(row_copy)

        return healed

    def reconstruct(self, tables: List[RawTable]) -> List[RawTable]:
        if not tables:
            return []

        # Sort tables by page number and table index
        sorted_tables = sorted(tables, key=lambda t: (t.page_number, t.table_index))
        reconstructed: List[RawTable] = []

        current_master: Optional[RawTable] = None

        for table in sorted_tables:
            if current_master is None:
                initial_rows = self.heal_rows(table.rows, table.column_count)
                current_master = RawTable(
                    page_number=table.page_number,
                    table_index=table.table_index,
                    headers=list(table.headers),
                    rows=initial_rows,
                    extraction_method=table.extraction_method,
                    confidence=table.confidence,
                )
                continue

            # Check if this table is a continuation of current_master:
            col_count_matches = (table.column_count == current_master.column_count)
            sim = self.header_similarity(current_master.headers, table.headers)
            
            is_repeated_header = False
            if table.rows and self.header_similarity(current_master.headers, table.rows[0]) > 0.80:
                is_repeated_header = True

            is_continuation = False
            if sim > 0.75 or (col_count_matches and not table.headers) or is_repeated_header:
                is_continuation = True

            if is_continuation:
                rows_to_add = list(table.rows)
                if is_repeated_header and rows_to_add:
                    rows_to_add = rows_to_add[1:]

                # Combine current rows with new rows and heal together
                all_combined_rows = current_master.rows + rows_to_add
                current_master.rows = self.heal_rows(all_combined_rows, current_master.column_count)
            else:
                reconstructed.append(current_master)
                current_master = RawTable(
                    page_number=table.page_number,
                    table_index=table.table_index,
                    headers=list(table.headers),
                    rows=self.heal_rows(table.rows, table.column_count),
                    extraction_method=table.extraction_method,
                    confidence=table.confidence,
                )

        if current_master is not None:
            reconstructed.append(current_master)

        return reconstructed
