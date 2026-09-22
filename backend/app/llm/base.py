import abc
import time
import logging
from typing import Type, TypeVar, Optional, List, Dict, Any, Tuple
from pydantic import BaseModel

logger = logging.getLogger("dataforge.llm.base")

T = TypeVar("T", bound=BaseModel)

class ProviderResponse(BaseModel):
    parsed: Optional[Any] = None
    raw_text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    model: str = ""
    provider: str = ""

class LLMProvider(abc.ABC):
    """Abstract Base Class for all LLM providers (Cloud & Local)."""

    def __init__(self, provider_id: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.provider_id = provider_id
        self.api_key = api_key or ""
        self.base_url = base_url or ""

    @abc.abstractmethod
    def generate_structured(
        self,
        schema: Type[T],
        system_prompt: str,
        user_prompt: str,
        model: str,
        images: Optional[List[bytes]] = None,
        temperature: float = 0.0,
        max_tokens: int = 16000,
        reasoning_mode: bool = False,
    ) -> ProviderResponse:
        """Generate a strictly typed response validated against a Pydantic schema."""
        pass

    @abc.abstractmethod
    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        images: Optional[List[bytes]] = None,
        temperature: float = 0.0,
        max_tokens: int = 16000,
    ) -> ProviderResponse:
        """Generate raw text response."""
        pass

    @abc.abstractmethod
    def test_connection(self, model: Optional[str] = None) -> Tuple[bool, str, int]:
        """Test provider connectivity. Returns (success, message, latency_ms)."""
        pass

    def estimate_tokens(self, text: str) -> int:
        """Heuristic token estimation: ~4 chars per token for English text."""
        return max(1, len(text) // 4)

    def calculate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cost_input_per_m: float,
        cost_output_per_m: float,
    ) -> float:
        """Calculate approximate USD cost."""
        input_cost = (prompt_tokens / 1_000_000.0) * cost_input_per_m
        output_cost = (completion_tokens / 1_000_000.0) * cost_output_per_m
        return round(input_cost + output_cost, 6)
