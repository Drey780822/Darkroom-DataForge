import logging
from typing import Optional, Dict, Any, Type, List, Tuple
from pydantic import BaseModel

from backend.app.llm.base import LLMProvider, ProviderResponse
from backend.app.llm.registry import ModelRegistry
from backend.app.llm.providers import (
    OpenAICompatibleProvider,
    AnthropicProvider,
    GoogleProvider,
    GroqProvider,
    OllamaProvider,
    OpenRouterProvider,
)

logger = logging.getLogger("dataforge.llm.router")

class EscalationLevel:
    LEVEL_1_NATIVE = "level_1_native"
    LEVEL_2_TABLES = "level_2_tables"
    LEVEL_3_LAYOUT = "level_3_layout"
    LEVEL_4_OCR = "level_4_ocr"
    LEVEL_5_LLM_TEXT = "level_5_llm_text"
    LEVEL_6_VISION = "level_6_vision"
    LEVEL_7_MULTI_MODEL = "level_7_multi_model"
    LEVEL_8_HUMAN_REVIEW = "level_8_human_review"

class ExtractionMode:
    FAST = "fast"
    BALANCED = "balanced"
    HIGH_ACCURACY = "high_accuracy"
    MAXIMUM_ACCURACY = "maximum_accuracy"

class LLMRouter:
    """Intelligent Model Router and Escalation Engine."""

    @classmethod
    def get_provider(cls, provider_id: str) -> LLMProvider:
        provider_id = provider_id.lower()
        if provider_id == "deepseek":
            return OpenAICompatibleProvider(provider_id="deepseek")
        elif provider_id == "anthropic":
            return AnthropicProvider()
        elif provider_id == "google":
            return GoogleProvider()
        elif provider_id == "groq":
            return GroqProvider()
        elif provider_id == "ollama":
            return OllamaProvider()
        elif provider_id == "openrouter":
            return OpenRouterProvider()
        else:
            return OpenAICompatibleProvider(provider_id=provider_id)

    @classmethod
    def execute_structured_with_fallback(
        cls,
        schema: Type[BaseModel],
        system_prompt: str,
        user_prompt: str,
        primary_provider: str,
        primary_model: str,
        fallback_provider: Optional[str] = None,
        fallback_model: Optional[str] = None,
        images: Optional[List[bytes]] = None,
        temperature: float = 0.0,
        max_tokens: int = 16000,
        reasoning_mode: bool = False,
    ) -> Tuple[ProviderResponse, str]:
        """Executes structured generation on primary model, falling back to secondary if primary fails."""
        try:
            provider = cls.get_provider(primary_provider)
            logger.info(f"Invoking {primary_provider}:{primary_model} for structured extraction...")
            res = provider.generate_structured(
                schema=schema,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=primary_model,
                images=images,
                temperature=temperature,
                max_tokens=max_tokens,
                reasoning_mode=reasoning_mode,
            )
            return res, f"{primary_provider}:{primary_model}"
        except Exception as primary_err:
            logger.warning(f"Primary model {primary_provider}:{primary_model} failed: {primary_err}")
            if fallback_provider and fallback_model:
                logger.info(f"Engaging fallback model {fallback_provider}:{fallback_model}...")
                fb_provider = cls.get_provider(fallback_provider)
                res = fb_provider.generate_structured(
                    schema=schema,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=fallback_model,
                    images=images,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    reasoning_mode=reasoning_mode,
                )
                return res, f"{fallback_provider}:{fallback_model} (fallback)"
            raise primary_err
