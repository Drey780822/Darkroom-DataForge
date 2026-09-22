import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import httpx

from backend.app.config import settings
from backend.app.llm.schemas import ModelMetadata, ProviderConfig, AIModelConfigSchema

logger = logging.getLogger("dataforge.llm.registry")

CREDENTIALS_FILE = settings.storage_path / "ai_credentials.json"

DEFAULT_MODELS: List[ModelMetadata] = [
    # DeepSeek
    ModelMetadata(
        provider="deepseek",
        model="deepseek-reasoner",
        display_name="DeepSeek Reasoner (R1)",
        context_window=64000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=True,
        cost_input_per_million=0.55,
        cost_output_per_million=2.19,
    ),
    ModelMetadata(
        provider="deepseek",
        model="deepseek-chat",
        display_name="DeepSeek V3 (Chat)",
        context_window=64000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=False,
        cost_input_per_million=0.14,
        cost_output_per_million=0.28,
    ),
    # Google
    ModelMetadata(
        provider="google",
        model="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        context_window=1000000,
        supports_json=True,
        supports_vision=True,
        supports_reasoning=False,
        cost_input_per_million=0.075,
        cost_output_per_million=0.30,
    ),
    ModelMetadata(
        provider="google",
        model="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        context_window=2000000,
        supports_json=True,
        supports_vision=True,
        supports_reasoning=True,
        cost_input_per_million=1.25,
        cost_output_per_million=5.00,
    ),
    # Anthropic
    ModelMetadata(
        provider="anthropic",
        model="claude-3-7-sonnet-20250219",
        display_name="Claude 3.7 Sonnet",
        context_window=200000,
        supports_json=True,
        supports_vision=True,
        supports_reasoning=True,
        cost_input_per_million=3.00,
        cost_output_per_million=15.00,
    ),
    ModelMetadata(
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        context_window=200000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=False,
        cost_input_per_million=0.80,
        cost_output_per_million=4.00,
    ),
    # Groq
    ModelMetadata(
        provider="groq",
        model="llama-3.3-70b-versatile",
        display_name="Groq Llama 3.3 70B",
        context_window=128000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=False,
        cost_input_per_million=0.59,
        cost_output_per_million=0.79,
    ),
    ModelMetadata(
        provider="groq",
        model="deepseek-r1-distill-llama-70b",
        display_name="Groq DeepSeek R1 Distill 70B",
        context_window=128000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=True,
        cost_input_per_million=0.75,
        cost_output_per_million=0.99,
    ),
    # Ollama (Local)
    ModelMetadata(
        provider="ollama",
        model="llama3.2",
        display_name="Ollama Llama 3.2 (Local)",
        context_window=32000,
        supports_json=True,
        supports_vision=True,
        supports_reasoning=False,
        cost_input_per_million=0.0,
        cost_output_per_million=0.0,
    ),
    ModelMetadata(
        provider="ollama",
        model="qwen2.5",
        display_name="Ollama Qwen 2.5 (Local)",
        context_window=32000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=False,
        cost_input_per_million=0.0,
        cost_output_per_million=0.0,
    ),
    ModelMetadata(
        provider="ollama",
        model="deepseek-r1:8b",
        display_name="Ollama DeepSeek R1 8B (Local)",
        context_window=32000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=True,
        cost_input_per_million=0.0,
        cost_output_per_million=0.0,
    ),
    # OpenAI
    ModelMetadata(
        provider="openai",
        model="gpt-4o",
        display_name="OpenAI GPT-4o",
        context_window=128000,
        supports_json=True,
        supports_vision=True,
        supports_reasoning=False,
        cost_input_per_million=2.50,
        cost_output_per_million=10.00,
    ),
    ModelMetadata(
        provider="openai",
        model="gpt-4o-mini",
        display_name="OpenAI GPT-4o Mini",
        context_window=128000,
        supports_json=True,
        supports_vision=True,
        supports_reasoning=False,
        cost_input_per_million=0.15,
        cost_output_per_million=0.60,
    ),
    # OpenRouter
    ModelMetadata(
        provider="openrouter",
        model="deepseek/deepseek-r1",
        display_name="OpenRouter DeepSeek R1",
        context_window=64000,
        supports_json=True,
        supports_vision=False,
        supports_reasoning=True,
        cost_input_per_million=0.55,
        cost_output_per_million=2.19,
    ),
]

PROVIDERS = [
    ProviderConfig(
        id="deepseek",
        name="DeepSeek",
        description="Reasoning & chat models specializing in complex tabular reasoning and low hallucination.",
        is_local=False,
        supports_vision=False,
        default_model="deepseek-reasoner",
        available_models=["deepseek-reasoner", "deepseek-chat"],
    ),
    ProviderConfig(
        id="ollama",
        name="Ollama (Local / On-Premise)",
        description="Run local open-weight models on your machine without external API requests. 100% confidential.",
        is_local=True,
        supports_vision=True,
        default_model="qwen2.5",
        available_models=["qwen2.5", "llama3.2", "deepseek-r1:8b", "mistral"],
    ),
    ProviderConfig(
        id="google",
        name="Google Gemini",
        description="Fast multimodal understanding with 1M+ token context windows and native PDF image analysis.",
        is_local=False,
        supports_vision=True,
        default_model="gemini-2.5-flash",
        available_models=["gemini-2.5-flash", "gemini-2.5-pro"],
    ),
    ProviderConfig(
        id="anthropic",
        name="Anthropic Claude",
        description="High precision document extraction with Claude 3.7 Sonnet reasoning mode.",
        is_local=False,
        supports_vision=True,
        default_model="claude-3-7-sonnet-20250219",
        available_models=["claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"],
    ),
    ProviderConfig(
        id="groq",
        name="Groq Cloud",
        description="Ultra-fast LPU inference for high-speed batch page processing.",
        is_local=False,
        supports_vision=False,
        default_model="llama-3.3-70b-versatile",
        available_models=["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"],
    ),
    ProviderConfig(
        id="openai",
        name="OpenAI / Compatible",
        description="OpenAI GPT-4o or any standard OpenAI-compatible server (vLLM, LM Studio).",
        is_local=False,
        supports_vision=True,
        default_model="gpt-4o-mini",
        available_models=["gpt-4o-mini", "gpt-4o"],
    ),
    ProviderConfig(
        id="openrouter",
        name="OpenRouter",
        description="Universal API gateway accessing all top commercial and open-weight models.",
        is_local=False,
        supports_vision=True,
        default_model="deepseek/deepseek-r1",
        available_models=["deepseek/deepseek-r1", "anthropic/claude-3.5-sonnet"],
    ),
]

class ModelRegistry:
    """Manages model metadata, credentials, and provider configurations."""

    @classmethod
    def _load_stored_credentials(cls) -> Dict[str, Dict[str, str]]:
        if CREDENTIALS_FILE.exists():
            try:
                with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to read credentials file: {e}")
        return {}

    @classmethod
    def _save_stored_credentials(cls, data: Dict[str, Dict[str, str]]):
        try:
            CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write credentials file: {e}")

    @classmethod
    def get_credential(cls, provider: str) -> Dict[str, str]:
        """Resolves API key and base URL from env vars or encrypted server storage."""
        stored = cls._load_stored_credentials().get(provider, {})
        env_key = os.getenv(f"{provider.upper()}_API_KEY", "")
        if provider == "google" and not env_key:
            env_key = os.getenv("GEMINI_API_KEY", "")
        env_url = os.getenv(f"{provider.upper()}_BASE_URL", "")

        api_key = stored.get("api_key") or env_key or ""
        base_url = stored.get("base_url") or env_url or ""

        # Defaults for specific providers
        if provider == "ollama" and not base_url:
            base_url = "http://localhost:11434"
        elif provider == "deepseek" and not base_url:
            base_url = "https://api.deepseek.com"
        elif provider == "openai" and not base_url:
            base_url = "https://api.openai.com/v1"
        elif provider == "groq" and not base_url:
            base_url = "https://api.groq.com/openai/v1"
        elif provider == "openrouter" and not base_url:
            base_url = "https://openrouter.ai/api/v1"

        return {"api_key": api_key, "base_url": base_url}

    @classmethod
    def set_credential(cls, provider: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        stored = cls._load_stored_credentials()
        current = stored.get(provider, {})
        if api_key is not None:
            current["api_key"] = api_key.strip()
        if base_url is not None:
            current["base_url"] = base_url.strip()
        stored[provider] = current
        cls._save_stored_credentials(stored)

    @classmethod
    def list_providers(cls) -> List[ProviderConfig]:
        providers = []
        for p in PROVIDERS:
            cred = cls.get_credential(p.id)
            is_configured = bool(cred.get("api_key")) or p.is_local
            p_copy = p.model_copy()
            p_copy.is_configured = is_configured
            providers.append(p_copy)
        return providers

    @classmethod
    def list_models(cls) -> List[ModelMetadata]:
        models = list(DEFAULT_MODELS)
        # Probe local Ollama if available
        ollama_cred = cls.get_credential("ollama")
        base_url = ollama_cred.get("base_url", "http://localhost:11434")
        try:
            resp = httpx.get(f"{base_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                for t in tags:
                    name = t.get("name")
                    if name and not any(m.model == name and m.provider == "ollama" for m in models):
                        models.append(
                            ModelMetadata(
                                provider="ollama",
                                model=name,
                                display_name=f"Ollama {name} (Local)",
                                context_window=32000,
                                supports_json=True,
                                supports_vision=False,
                                supports_reasoning=True if "r1" in name.lower() else False,
                                cost_input_per_million=0.0,
                                cost_output_per_million=0.0,
                            )
                        )
        except Exception:
            pass  # Ollama not running locally
        return models

    @classmethod
    def get_model_metadata(cls, provider: str, model: str) -> Optional[ModelMetadata]:
        for m in cls.list_models():
            if m.provider == provider and m.model == model:
                return m
        # Fallback dynamic metadata
        return ModelMetadata(
            provider=provider,
            model=model,
            display_name=f"{provider.capitalize()} {model}",
            context_window=32000,
            supports_json=True,
            supports_vision=False,
            supports_reasoning=False,
        )
