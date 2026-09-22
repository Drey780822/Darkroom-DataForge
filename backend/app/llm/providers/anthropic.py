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

logger = logging.getLogger("dataforge.llm.anthropic")

T = TypeVar("T", bound=BaseModel)

class AnthropicProvider(LLMProvider):
    """Anthropic Claude API Provider (Claude 3.7 Sonnet, Claude 3.5 Haiku)."""

    def __init__(self, provider_id: str = "anthropic", api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(provider_id, api_key, base_url)
        if not self.api_key:
            cred = ModelRegistry.get_credential("anthropic")
            self.api_key = cred.get("api_key", "")
        self.base_url = "https://api.anthropic.com/v1"

    def _get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def test_connection(self, model: Optional[str] = None) -> Tuple[bool, str, int]:
        target_model = model or "claude-3-5-haiku-20241022"
        start = time.time()
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json={
                        "model": target_model,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 5,
                    },
                )
                latency = int((time.time() - start) * 1000)
                if res.status_code == 200:
                    return True, "Connected to Claude successfully", latency
                return False, f"Claude error HTTP {res.status_code}: {res.text[:200]}", latency
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return False, f"Claude connection error: {e}", latency

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
        schema_dict = schema.model_json_schema()

        # We can use Claude's tool_choice to force strict structured JSON
        tools = [
            {
                "name": "submit_extracted_data",
                "description": "Submit strictly structured data extracted from the document.",
                "input_schema": schema_dict,
            }
        ]

        content_items = []
        if images:
            for img_bytes in images:
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content_items.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64
                    }
                })
        content_items.append({"type": "text", "text": user_prompt})

        payload = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": content_items}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": tools,
            "tool_choice": {"type": "tool", "name": "submit_extracted_data"},
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{self.base_url}/messages",
                    headers=self._get_headers(),
                    json=payload,
                )
                if resp.status_code != 200:
                    raise ValueError(f"Claude API error {resp.status_code}: {resp.text}")

                data = resp.json()
                content = data.get("content", [])
                tool_input = None
                raw_text = ""
                for c in content:
                    if c.get("type") == "tool_use" and c.get("name") == "submit_extracted_data":
                        tool_input = c.get("input", {})
                        raw_text = json.dumps(tool_input)
                        break

                if tool_input is None:
                    # Fallback to text parsing
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    raw_text = " ".join(text_parts)
                    clean_json = extract_json_from_text(raw_text)
                    parsed_obj = schema.model_validate_json(clean_json)
                else:
                    parsed_obj = schema.model_validate(tool_input)

                usage = data.get("usage", {})
                p_tokens = usage.get("input_tokens", 0)
                c_tokens = usage.get("output_tokens", 0)

                meta = ModelRegistry.get_model_metadata("anthropic", model)
                cost = self.calculate_cost(
                    p_tokens,
                    c_tokens,
                    meta.cost_input_per_million if meta else 3.0,
                    meta.cost_output_per_million if meta else 15.0,
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
                    provider="anthropic",
                )
        except Exception as e:
            logger.exception(f"Claude structured extraction failed: {e}")
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
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        with httpx.Client(timeout=90.0) as client:
            resp = client.post(
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json=payload,
            )
            data = resp.json()
            content = data.get("content", [])
            raw_text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
            usage = data.get("usage", {})
            p_tokens = usage.get("input_tokens", 0)
            c_tokens = usage.get("output_tokens", 0)
            latency = int((time.time() - start_time) * 1000)
            return ProviderResponse(
                raw_text=raw_text,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=p_tokens + c_tokens,
                latency_ms=latency,
                model=model,
                provider="anthropic",
            )
