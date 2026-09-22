import json
import time
import logging
from typing import Type, TypeVar, Optional, List, Tuple
import httpx
from pydantic import BaseModel

from backend.app.llm.base import LLMProvider, ProviderResponse
from backend.app.llm.registry import ModelRegistry
from backend.app.llm.providers.openai_compatible import extract_json_from_text

logger = logging.getLogger("dataforge.llm.ollama")

T = TypeVar("T", bound=BaseModel)

class OllamaProvider(LLMProvider):
    """Local Ollama provider for completely offline, sensitive research processing."""

    def __init__(self, provider_id: str = "ollama", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(provider_id, api_key, base_url)
        if not self.base_url:
            cred = ModelRegistry.get_credential("ollama")
            self.base_url = cred.get("base_url") or "http://localhost:11434"

    def test_connection(self, model: Optional[str] = None) -> Tuple[bool, str, int]:
        start = time.time()
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(f"{self.base_url.rstrip('/')}/api/tags")
                latency = int((time.time() - start) * 1000)
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    return True, f"Ollama online. Found {len(models)} model(s): {', '.join(models[:3])}", latency
                return False, f"Ollama HTTP {res.status_code}", latency
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return False, f"Ollama unreachable on {self.base_url}: {e}", latency

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
        start_time = time.time()
        schema_json_str = json.dumps(schema.model_json_schema(), indent=2)

        augmented_system = (
            f"{system_prompt}\n\n"
            f"You are a strictly constrained data extraction engine.\n"
            f"You MUST return ONLY a valid JSON object strictly complying with this JSON Schema:\n"
            f"{schema_json_str}\n"
            f"Do NOT include markdown fences, comments, or intro text. Pure JSON only."
        )

        messages = [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": model,
            "messages": messages,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(
                    f"{self.base_url.rstrip('/')}/api/chat",
                    json=payload,
                )
                if resp.status_code != 200:
                    raise ValueError(f"Ollama error {resp.status_code}: {resp.text}")

                data = resp.json()
                raw_text = data.get("message", {}).get("content", "")
                clean_json = extract_json_from_text(raw_text)
                parsed_obj = schema.model_validate_json(clean_json)

                p_tokens = data.get("prompt_eval_count", self.estimate_tokens(user_prompt + system_prompt))
                c_tokens = data.get("eval_count", self.estimate_tokens(raw_text))
                latency = int((time.time() - start_time) * 1000)

                return ProviderResponse(
                    parsed=parsed_obj,
                    raw_text=raw_text,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=p_tokens + c_tokens,
                    estimated_cost_usd=0.0,  # Local is completely free
                    latency_ms=latency,
                    model=model,
                    provider="ollama",
                )
        except Exception as e:
            logger.exception(f"Ollama generation failed: {e}")
            raise

    def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        images: Optional[List[bytes]] = None,
        temperature: float = 0.0,
        max_tokens: int = 16000,
    ) -> ProviderResponse:
        start_time = time.time()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.base_url.rstrip('/')}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            data = resp.json()
            raw_text = data.get("message", {}).get("content", "")
            latency = int((time.time() - start_time) * 1000)
            return ProviderResponse(
                raw_text=raw_text,
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                latency_ms=latency,
                model=model,
                provider="ollama",
            )
