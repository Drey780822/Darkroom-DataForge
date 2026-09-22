import os
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.llm.schemas import DocumentIntelligenceMap, ChunkExtractionResponse
from backend.app.services.document_inspector import DocumentInspectorService

logger = logging.getLogger("dataforge.services.chunk_manager")

CACHE_DIR = settings.storage_path / "temp" / "llm_cache"

class ExtractionChunk(BaseModel):
    chunk_index: int
    page_start: int
    page_end: int
    pages: List[int]
    is_continuation: bool = False
    text: str
    previous_overlap_text: Optional[str] = None

class ChunkManagerService:
    """Manages table-aware document chunking, continuation overlaps, and response caching."""

    @classmethod
    def create_chunks(
        cls,
        file_path: str,
        doc_map: DocumentIntelligenceMap,
        pages_to_process: Optional[List[int]] = None,
        chunk_size: int = 4,
    ) -> List[ExtractionChunk]:
        all_pages = pages_to_process if pages_to_process else list(range(1, doc_map.page_count + 1))
        all_pages = sorted(list(set(all_pages)))
        if not all_pages:
            return []

        chunks: List[ExtractionChunk] = []
        i = 0
        chunk_idx = 0

        # Build map of continuation page groups
        continuation_lookup = {}
        for group in doc_map.continuation_groups:
            for p in group[1:]:
                continuation_lookup[p] = True

        while i < len(all_pages):
            batch_pages = all_pages[i : i + chunk_size]
            start_p = batch_pages[0]
            end_p = batch_pages[-1]

            # Collect text for all pages in this chunk
            chunk_text_parts = []
            for p in batch_pages:
                p_text = DocumentInspectorService.get_page_text(file_path, p)
                chunk_text_parts.append(f"=== PAGE {p} ===\n{p_text}")
            chunk_text = "\n\n".join(chunk_text_parts)

            # Determine continuation status and overlap context
            is_cont = continuation_lookup.get(start_p, False)
            prev_overlap = None
            if is_cont and start_p > 1:
                prev_text = DocumentInspectorService.get_page_text(file_path, start_p - 1)
                lines = [l for l in prev_text.split("\n") if l.strip()]
                prev_overlap = "\n".join(lines[-15:]) if lines else None

            chunks.append(
                ExtractionChunk(
                    chunk_index=chunk_idx,
                    page_start=start_p,
                    page_end=end_p,
                    pages=batch_pages,
                    is_continuation=is_cont,
                    text=chunk_text,
                    previous_overlap_text=prev_overlap,
                )
            )

            # Contextual overlap: If end page is in the middle of a continuation table,
            # include it in the next chunk as well
            if end_p in continuation_lookup and i + chunk_size < len(all_pages):
                i += max(1, chunk_size - 1)
            else:
                i += chunk_size
            chunk_idx += 1

        return chunks

    @classmethod
    def get_cache_key(
        cls,
        doc_hash: str,
        chunk_start: int,
        chunk_end: int,
        model: str,
        prompt_version: str,
        profile: str = "default",
    ) -> str:
        raw = f"{doc_hash}_{chunk_start}_{chunk_end}_{model}_{prompt_version}_{profile}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def get_cached_response(cls, cache_key: str) -> Optional[ChunkExtractionResponse]:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ChunkExtractionResponse.model_validate(data)
            except Exception as e:
                logger.warning(f"Failed to read cache {cache_key}: {e}")
        return None

    @classmethod
    def set_cached_response(cls, cache_key: str, response: ChunkExtractionResponse):
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"{cache_key}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(response.model_dump(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache {cache_key}: {e}")
