import json
import time
import re
import logging
from typing import Type, TypeVar, Optional, List, Tuple
import httpx
from pydantic import BaseModel

from backend.app.llm.base import LLMProvider, ProviderResponse
from backend.app.llm.registry import ModelRegistry

logger = logging.getLogger("dataforge.llm.openai_compatible")

T = TypeVar("T", bound=BaseModel)

def extract_json_from_text(text: str) -> str:
    """Robustly extract JSON string from markdown code fences or raw text anywhere in response."""
    text = text.strip()
    # 1. Search for markdown code fence anywhere in text
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # 2. Search for outermost {...} or [...]
    brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if brace_match:
        return brace_match.group(1).strip()
    return text

class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI, DeepSeek, Grok, vLLM, and LM Studio."""

    def __init__(self, provider_id: str = "openai", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(provider_id, api_key, base_url)
        if not self.base_url:
            cred = ModelRegistry.get_credential(provider_id)
            self.base_url = cred.get("base_url") or "https://api.openai.com/v1"
        if not self.api_key:
            cred = ModelRegistry.get_credential(provider_id)
            self.api_key = cred.get("api_key", "")

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        return headers

    def test_connection(self, model: Optional[str] = None) -> Tuple[bool, str, int]:
        target_model = model or ("deepseek-chat" if self.provider_id == "deepseek" else "gpt-4o-mini")
        start = time.time()
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=self._get_headers(),
                    json={
                        "model": target_model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 5,
                    },
                )
                latency = int((time.time() - start) * 1000)
                if res.status_code == 200:
                    return True, "Connected successfully", latency
                else:
                    return False, f"HTTP {res.status_code}: {res.text[:200]}", latency
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return False, str(e), latency

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
        
        # Enforce JSON schema requirement in the system prompt
        schema_json_str = json.dumps(schema.model_json_schema(), indent=2)
        augmented_system = (
            f"{system_prompt}\n\n"
            f"CRITICAL REQUIREMENT:\n"
            f"You MUST return ONLY a valid JSON object matching this exact JSON Schema:\n"
            f"{schema_json_str}\n"
            f"Do not include any greeting, preamble, or commentary. Output pure JSON."
        )

        messages = [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": user_prompt},
        ]

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        # Attempt with retries for transient errors / 429
        last_error = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers=self._get_headers(),
                        json=payload,
                    )
                    
                    if resp.status_code in [429, 500, 502, 503, 504]:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    
                    if resp.status_code != 200:
                        raise ValueError(f"Provider API Error {resp.status_code}: {resp.text}")

                    data = resp.json()
                    raw_content = data["choices"][0]["message"]["content"] or "{}"
                    usage = data.get("usage", {})
                    p_tokens = usage.get("prompt_tokens", 0)
                    c_tokens = usage.get("completion_tokens", 0)

                    # Extract and parse JSON
                    json_str = extract_json_from_text(raw_content)
                    parsed_obj = schema.model_validate_json(json_str)

                    meta = ModelRegistry.get_model_metadata(self.provider_id, model)
                    cost = self.calculate_cost(
                        p_tokens,
                        c_tokens,
                        meta.cost_input_per_million if meta else 0.0,
                        meta.cost_output_per_million if meta else 0.0,
                    )
                    latency = int((time.time() - start_time) * 1000)

                    return ProviderResponse(
                        parsed=parsed_obj,
                        raw_text=raw_content,
                        prompt_tokens=p_tokens,
                        completion_tokens=c_tokens,
                        total_tokens=p_tokens + c_tokens,
                        estimated_cost_usd=cost,
                        latency_ms=latency,
                        model=model,
                        provider=self.provider_id,
                    )
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(1.0 * (attempt + 1))

        raise RuntimeError(f"Failed to generate structured response after 3 attempts: {last_error}")

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
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            )
            if resp.status_code != 200:
                raise ValueError(f"Provider API Error {resp.status_code}: {resp.text}")
            data = resp.json()
            raw_content = data["choices"][0]["message"]["content"] or ""
            usage = data.get("usage", {})
            p_tokens = usage.get("prompt_tokens", 0)
            c_tokens = usage.get("completion_tokens", 0)
            latency = int((time.time() - start_time) * 1000)

            return ProviderResponse(
                raw_text=raw_content,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=p_tokens + c_tokens,
                latency_ms=latency,
                model=model,
                provider=self.provider_id,
            )
