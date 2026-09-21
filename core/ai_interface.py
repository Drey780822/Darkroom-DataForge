from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AISuggestion(BaseModel):
    category: str                       # e.g., "column_mapping", "schema_suggestion", "anomaly_explanation"
    suggestion: str
    confidence: float = 0.85
    rationale: str
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    requires_human_approval: bool = True


class BaseAIAssistant(ABC):
    """Clean interface for optional LLM / AI providers (Gemini, OpenAI, local models)."""

    def __init__(self, provider_name: str = "none", model_name: str = ""):
        self.provider_name = provider_name
        self.model_name = model_name

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the AI provider credentials and network are active."""
        pass

    @abstractmethod
    def suggest_schema(self, table_sample: List[List[str]]) -> List[AISuggestion]:
        """Provides AI-guided semantic field naming and type suggestions."""
        pass

    @abstractmethod
    def explain_anomaly(self, record_context: Dict[str, Any], issue_description: str) -> AISuggestion:
        """Generates a human-intelligible explanation for a validation anomaly."""
        pass


class MockDisabledAIAssistant(BaseAIAssistant):
    """Default local provider when external AI APIs are disabled (strict offline operation)."""

    def __init__(self):
        super().__init__(provider_name="none", model_name="offline")

    def is_configured(self) -> bool:
        return False

    def suggest_schema(self, table_sample: List[List[str]]) -> List[AISuggestion]:
        return []

    def explain_anomaly(self, record_context: Dict[str, Any], issue_description: str) -> AISuggestion:
        return AISuggestion(
            category="anomaly_explanation",
            suggestion="Offline rule validation applied. AI external explanation disabled.",
            confidence=1.0,
            rationale="All processing strictly local.",
            requires_human_approval=False,
        )
