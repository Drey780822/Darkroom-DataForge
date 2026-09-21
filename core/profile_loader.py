from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from models.profile import ExtractionProfile
from models.document import DocumentType


class ProfileLoader:
    """Discovers, parses, and manages YAML extraction profiles."""

    def __init__(self, profiles_dir: Optional[str] = None):
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir).resolve()
        else:
            base = Path(__file__).resolve().parent.parent
            self.profiles_dir = base / "config" / "profiles"

        self._profiles: Dict[str, ExtractionProfile] = {}
        self.load_profiles()

    def load_profiles(self) -> None:
        self._profiles.clear()
        if not self.profiles_dir.exists():
            return

        for p_path in self.profiles_dir.glob("*.yaml"):
            try:
                with open(p_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict) and "name" in data:
                    profile = ExtractionProfile.model_validate(data)
                    self._profiles[profile.name] = profile
            except Exception as e:
                print(f"[ProfileLoader] Failed to load profile from {p_path}: {e}")

    def get_profile(self, name: str) -> Optional[ExtractionProfile]:
        return self._profiles.get(name)

    def get_all_profiles(self) -> List[ExtractionProfile]:
        return list(self._profiles.values())

    def get_profile_by_document_type(self, doc_type: DocumentType) -> Optional[ExtractionProfile]:
        for p in self._profiles.values():
            if p.document_type == doc_type:
                return p
        return None

    def match_profile(self, filename: str, sample_text: str = "") -> Optional[ExtractionProfile]:
        """Matches a document against registered profiles using filename regex and keyword patterns."""
        best_profile: Optional[ExtractionProfile] = None
        best_score = 0

        sample_lower = sample_text.lower()
        filename_clean = filename.lower()

        for profile in self._profiles.values():
            if profile.name == "generic_table":
                continue

            score = 0
            patterns = profile.matching_patterns or {}

            # 1. Filename regex match
            fn_regex = patterns.get("filename_regex")
            if fn_regex:
                try:
                    if re.search(fn_regex, filename_clean):
                        score += 5
                except re.error:
                    pass

            # 2. Keyword matches
            keywords = patterns.get("keywords", [])
            for kw in keywords:
                if kw.lower() in sample_lower:
                    score += 2
                if kw.lower() in filename_clean:
                    score += 3

            if score > best_score:
                best_score = score
                best_profile = profile

        return best_profile if best_score >= 4 else None


_default_loader: Optional[ProfileLoader] = None


def get_profile_loader() -> ProfileLoader:
    global _default_loader
    if _default_loader is None:
        _default_loader = ProfileLoader()
    return _default_loader
