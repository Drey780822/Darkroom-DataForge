import json
import time
import base64
import logging
from typing import Type, TypeVar, Optional, List, Tuple
import httpx
from pydantic import BaseModel

from backend.app.llm.base import LLMProvider, ProviderResponse
from backend.app.llm.registry import ModelRegistry
from backend.app.llm.providers.openai_compatible import extract_json_from_text

logger = logging.getLogger("dataforge.llm.google")

T = TypeVar("T", bound=BaseModel)

class GoogleProvider(LLMProvider):
    """Google Gemini API Provider with native structured JSON schema and vision support."""

    def __init__(self, provider_id: str = "google", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(provider_id, api_key, base_url)
        if not self.api_key:
            cred = ModelRegistry.get_credential("google")
            self.api_key = cred.get("api_key", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def test_connection(self, model: Optional[str] = None) -> Tuple[bool, str, int]:
        target_model = model or "gemini-2.5-flash"
        start = time.time()
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{self.base_url}/models/{target_model}:generateContent?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": "ping"}]}],
                        "generationConfig": {"maxOutputTokens": 5},
                    },
                )
                latency = int((time.time() - start) * 1000)
                if res.status_code == 200:
                    return True, "Connected to Gemini successfully", latency
                return False, f"Gemini error HTTP {res.status_code}: {res.text[:200]}", latency
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return False, f"Gemini connection error: {e}", latency

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
        
        parts = []
        # Add vision images if present
        if images:
            for img_bytes in images:
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": b64
                    }
                })
        parts.append({"text": user_prompt})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                    json=payload,
                )
                if resp.status_code != 200:
                    raise ValueError(f"Gemini API error {resp.status_code}: {resp.text}")

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No response candidates returned by Gemini.")

                content_parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = content_parts[0].get("text", "{}") if content_parts else "{}"

                clean_json = extract_json_from_text(raw_text)
                parsed_obj = schema.model_validate_json(clean_json)

                usage = data.get("usageMetadata", {})
                p_tokens = usage.get("promptTokenCount", self.estimate_tokens(user_prompt + system_prompt))
                c_tokens = usage.get("candidatesTokenCount", self.estimate_tokens(raw_text))

                meta = ModelRegistry.get_model_metadata("google", model)
                cost = self.calculate_cost(
                    p_tokens,
                    c_tokens,
                    meta.cost_input_per_million if meta else 0.075,
                    meta.cost_output_per_million if meta else 0.30,
                )
                latency = int((time.time() - start_time) * 1000)

                return ProviderResponse(
                    parsed=parsed_obj,
                    raw_text=raw_text,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=p_tokens + c_tokens,
                    estimated_cost_usd=cost,
                    latency_ms=latency,
                    model=model,
                    provider="google",
                )
        except Exception as e:
            logger.exception(f"Gemini structured extraction failed: {e}")
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
        parts = []
        if images:
            for img_bytes in images:
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
        parts.append({"text": user_prompt})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
                json=payload,
            )
            data = resp.json()
            candidates = data.get("candidates", [])
            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "") if candidates else ""
            latency = int((time.time() - start_time) * 1000)
            return ProviderResponse(
                raw_text=raw_text,
                prompt_tokens=data.get("usageMetadata", {}).get("promptTokenCount", 0),
                completion_tokens=data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                total_tokens=data.get("usageMetadata", {}).get("totalTokenCount", 0),
                latency_ms=latency,
                model=model,
                provider="google",
            )
